from fastapi import APIRouter, HTTPException, Depends, Query, Security, BackgroundTasks, Request
from fastapi.security import APIKeyHeader, APIKeyQuery
from typing import Optional, Dict
from datetime import datetime
import concurrent.futures

from app.core.city_manager import city_manager
from app.core.db import db_manager, get_redis_client
from app.models.weather import WeatherRecord
from app.core.client_key_manager import client_key_manager
from app.worker.fetchers import FetcherRegistry
from app.core.timezone import get_beijing_now, get_beijing_date, to_beijing_datetime
from app.core.logger import logger

router = APIRouter()


# 定义 API Key 来源 (Header 或 Query)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="key", auto_error=False)

async def get_api_key(
    request: Request,
    key_header: str = Security(api_key_header),
    key_query: str = Security(api_key_query)
):
    """
    获取并验证 API Key (含 IP 和限流检查)
    """
    key = key_header or key_query
    if not key:
        raise HTTPException(status_code=401, detail="Missing API Key")
    
    # 获取真实 IP (考虑代理)
    client_ip = request.client.host
    if "x-forwarded-for" in request.headers:
        client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
        
    is_valid, error_msg = client_key_manager.validate_access(key, client_ip)
    if not is_valid:
        status_code = 429 if "Rate limit" in error_msg else 403
        raise HTTPException(status_code=status_code, detail=error_msg)
        
    return key

def save_weather_data(city_id: str, city_name: str, new_data: dict):
    """
    后台任务: 保存天气数据到数据库
    """
    try:
        db = db_manager.get_db()
        current_time_str = get_beijing_now().isoformat()
        
        # 查询城市的 adcode
        city_info = db.cities.find_one({"_id": city_id})
        adcode = city_info.get("adcode") if city_info else city_id + "000000"
        
        set_payload = {
            "last_updated_at": current_time_str,
            "city_name": city_name,
            "adcode": adcode,
        }
        for channel, data in new_data.items():
            set_payload[f"sources.{channel}"] = data
            
        db.weather_records.update_one(
            {"_id": city_id},
            {"$set": set_payload},
            upsert=True
        )
        logger.info(f"Background update success for {city_name} ({city_id}), channels: {list(new_data.keys())}")
    except Exception as e:
        logger.error(f"Background update failed for {city_name} ({city_id}): {e}")

async def _get_weather_core(
    city: str,
    background_tasks: BackgroundTasks,
    api_key: str
) -> dict:
    """
    获取指定城市天气核心逻辑 (包含缓存检测、多源实时聚合、异步回写)
    """
    # 1. 记录调用统计
    client_key_manager.track_usage(api_key)
    
    # 2. 解析城市
    city_info = city_manager.resolve_city(city)
    if not city_info:
        raise HTTPException(status_code=404, detail=f"City not found: {city}")
        
    city_id = city_info["_id"]
    city_name = city_info["name"]
    
    # 3. 查询数据库
    db = db_manager.get_db()
    weather_doc = db.weather_records.find_one({"_id": city_id})
    
    # 4. 检查缓存有效性
    need_update = True
    current_data = {}
    last_updated = None
    
    if weather_doc:
        last_updated = weather_doc.get("last_updated_at")
        current_data = weather_doc.get("sources", {})
        
        last_updated_dt = None
        if isinstance(last_updated, str):
            try:
                last_updated_dt = datetime.fromisoformat(last_updated)
            except ValueError:
                pass
        elif isinstance(last_updated, datetime):
            last_updated_dt = last_updated
            
        # 如果是今天的数据 (以北京时间为准)，则不需要更新
        if last_updated_dt and to_beijing_datetime(last_updated_dt).date() == get_beijing_date():
            # 检查是否缺失活跃渠道数据
            active_channels = db.channel_configs.find({"is_active": True})
            active_channel_names = [c["_id"] for c in active_channels]
            missing_channels = [c for c in active_channel_names if c not in current_data]
            
            if not missing_channels:
                need_update = False
            else:
                logger.info(f"Data incomplete for {city_name} (missing {missing_channels}), forcing refresh...")

    # 5. 如果缓存有效，直接返回
    if not need_update:
        return {
            "city_name": city_name,
            "_id": city_id,
            "last_updated_at": last_updated,
            "sources": current_data
        }
        
    # 6. 缓存失效，实时抓取
    logger.info(f"Data stale for {city_name}, fetching fresh data...")
    
    redis_client = get_redis_client()
    active_channels = list(db.channel_configs.find({"is_active": True}))
    new_sources_data = {}
    
    if current_data:
        new_sources_data = current_data.copy()
        
    def fetch_channel_data(config):
        channel_name = config["_id"]
        fetcher = FetcherRegistry.get_fetcher(channel_name, db, redis_client)
        if not fetcher:
            return None
        try:
            raw = fetcher.fetch(city_id)
            normalized = fetcher.normalize(raw)
            return channel_name, [w.model_dump() for w in normalized]
        except Exception as e:
            logger.error(f"Real-time fetch failed for {channel_name}: {e}")
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(active_channels) + 1) as executor:
        future_to_channel = {executor.submit(fetch_channel_data, config): config for config in active_channels}
        
        for future in concurrent.futures.as_completed(future_to_channel):
            result = future.result()
            if result:
                channel_name, data = result
                new_sources_data[channel_name] = data
                
    # 7. 后台异步入库
    background_tasks.add_task(save_weather_data, city_id, city_name, new_sources_data)
    
    return {
        "city_name": city_name,
        "_id": city_id,
        "last_updated_at": get_beijing_now().isoformat(),
        "sources": new_sources_data
    }


@router.get("", response_model=WeatherRecord, summary="获取指定城市天气 (Query 参数)")
async def get_weather_by_query(
    background_tasks: BackgroundTasks,
    city: Optional[str] = Query(None, description="城市名称或 ID (如: 北京, 101010100)"),
    api_key: str = Depends(get_api_key)
):
    """
    获取指定城市天气信息 (支持 Query 传参: ?city=北京)
    """
    if not city:
        raise HTTPException(status_code=400, detail="Missing required query parameter: city")
    return await _get_weather_core(city, background_tasks, api_key)

@router.get("/{city}", response_model=WeatherRecord, summary="获取指定城市天气 (Path 参数)")
async def get_weather_by_path(
    city: str,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(get_api_key)
):
    """
    获取指定城市天气信息 (支持 Path 传参: /api/v1/weather/北京)
    """
    return await _get_weather_core(city, background_tasks, api_key)
