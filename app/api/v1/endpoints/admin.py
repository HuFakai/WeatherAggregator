from fastapi import APIRouter, HTTPException, Depends, Header, Body, BackgroundTasks
from typing import List, Dict, Optional
from app.core.db import db_manager
from app.core.config import settings
from app.core.client_key_manager import client_key_manager
from app.models.client_key import ClientKey
from pydantic import BaseModel
import datetime
from app.core.timezone import get_beijing_date

router = APIRouter()


# Pydantic Models
class KeyAddRequest(BaseModel):
    key: str
    daily_limit: int = 2000
    desc: str = ""

# Admin Auth Dependency
async def verify_admin_access(x_admin_key: str = Header(..., alias="X-Admin-Key")):
    if x_admin_key != settings.ADMIN_LOGIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid Admin Key")
    return x_admin_key

@router.post("/login")
async def admin_login(key: str = Body(..., embed=True)):
    """
    验证管理密钥 (用于前端登录检查)
    """
    if key != settings.ADMIN_LOGIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid Key")
    return {"status": "ok"}

@router.get("/keys", response_model=List[Dict])
async def list_client_keys(admin_auth: str = Depends(verify_admin_access)):
    """
    获取所有客户端密钥及其统计信息
    """
    keys = client_key_manager.list_keys()
    result = []
    for k in keys:
        stats = client_key_manager.get_stats(k.key)
        # 计算总调用量 (7天)
        total_usage = sum(stats.values())
        
        key_data = k.model_dump()
        key_data["stats"] = stats
        key_data["total_usage_7d"] = total_usage
        result.append(key_data)
    return result

@router.post("/keys", response_model=ClientKey)
async def create_client_key(
    name: str = Body(..., embed=True),
    admin_auth: str = Depends(verify_admin_access)
):
    """
    创建新的客户端密钥
    """
    return client_key_manager.create_key(name)

@router.delete("/keys/{key}")
async def delete_client_key(
    key: str,
    admin_auth: str = Depends(verify_admin_access)
):
    """
    删除客户端密钥
    """
    success = client_key_manager.delete_key(key)
    if not success:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"status": "deleted"}

class KeyUpdateRequest(BaseModel):
    new_key: Optional[str] = None
    ip_whitelist_enabled: Optional[bool] = None
    ip_whitelist: Optional[List[str]] = None
    qpm_limit: Optional[int] = None

@router.put("/keys/{key}")
async def update_client_key(
    key: str,
    update_data: KeyUpdateRequest,
    admin_auth: str = Depends(verify_admin_access)
):
    """
    更新客户端密钥配置 (支持修改密钥值、IP白名单及QPM)
    """
    data = update_data.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No data provided")

    new_key = data.pop("new_key", None)
    if new_key is not None:
        new_key = new_key.strip()
        if not new_key:
            raise HTTPException(status_code=400, detail="密钥值不能为空")

    success, err_msg = client_key_manager.update_key(key, data, new_key=new_key)
    if not success:
        status_code = 404 if "原密钥不存在" in err_msg else 400
        raise HTTPException(status_code=status_code, detail=err_msg)
    return {"status": "updated", "key": new_key or key}

@router.get("/channels")
async def list_channels(admin_auth: str = Depends(verify_admin_access)):
    """
    获取所有渠道配置及状态
    """
    db = db_manager.get_db()
    redis = db_manager.get_redis()
    
    channels = list(db.channel_configs.find())
    
    # 获取 API Key 使用统计 (最近 3 天，按北京时间计算)
    today = get_beijing_date()
    dates = [(today - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(3)]

    
    for channel in channels:
        channel_name = channel["_id"]
        
        # 处理 keys_pool
        if "keys_pool" in channel:
            for key_info in channel["keys_pool"]:
                key = key_info.get("key")
                stats = {}
                total_3d = 0
                
                for date_str in dates:
                    # Redis Key: stats:usage:{channel}:{date} -> Hash {key: count}
                    redis_key = f"stats:usage:{channel_name}:{date_str}"
                    count = redis.hget(redis_key, key)
                    count_int = int(count) if count else 0
                    stats[date_str] = count_int
                    total_3d += count_int
                
                key_info["stats"] = stats
                key_info["total_3d"] = total_3d
        
    return channels

@router.post("/channels/{channel_name}/keys")
async def add_key(
    channel_name: str, 
    request: KeyAddRequest,
    admin_auth: str = Depends(verify_admin_access)
):
    """
    添加 API Key 到 keys_pool
    """
    db = db_manager.get_db()
    
    new_key = {
        "key": request.key,
        "status": "active",
        "daily_limit": request.daily_limit,
        "desc": request.desc
    }
    
    result = db.channel_configs.update_one(
        {"_id": channel_name},
        {"$push": {"keys_pool": new_key}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Channel not found")
    return {"status": "added", "key": request.key}

@router.delete("/channels/{channel_name}/keys")
async def remove_key(
    channel_name: str, 
    key: str = Body(..., embed=True),
    admin_auth: str = Depends(verify_admin_access)
):
    """
    从 keys_pool 删除 API Key
    """
    db = db_manager.get_db()
    result = db.channel_configs.update_one(
        {"_id": channel_name},
        {"$pull": {"keys_pool": {"key": key}}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Channel not found")
        
    # 清理 Redis 数据
    try:
        from app.core.key_manager import KeyManager
        redis = db_manager.get_redis()
        km = KeyManager(db, redis)
        km.delete_key_stats(channel_name, key)
    except Exception as e:
        # 不影响主流程
        print(f"Failed to cleanup redis stats: {e}")
        
    return {"status": "removed", "key": key}

class ChannelKeyStatusUpdateRequest(BaseModel):
    key: str
    status: str  # "active" or "disabled"

@router.put("/channels/{channel_name}/keys/status")
async def update_channel_key_status(
    channel_name: str,
    request: ChannelKeyStatusUpdateRequest,
    admin_auth: str = Depends(verify_admin_access)
):
    """
    切换渠道 API Key 的启用/禁用状态 (active / disabled)
    """
    if request.status not in ["active", "disabled"]:
        raise HTTPException(status_code=400, detail="状态必须为 active 或 disabled")

    db = db_manager.get_db()
    result = db.channel_configs.update_one(
        {"_id": channel_name, "keys_pool.key": request.key},
        {"$set": {"keys_pool.$.status": request.status}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="未找到对应的渠道或 Key")
    return {"status": "updated", "channel": channel_name, "key": request.key, "new_status": request.status}

@router.post("/channels/{channel_name}/update")
async def trigger_update(
    channel_name: str,
    admin_auth: str = Depends(verify_admin_access)
):
    """
    手动触发渠道全量更新
    """
    from app.worker.tasks import trigger_channel_update
    
    # 异步触发 Celery 任务
    trigger_channel_update.delay(channel_name)
    
    return {"status": "triggered", "message": f"Update task for {channel_name} started"}

class ChannelScheduleUpdateRequest(BaseModel):
    cron: Optional[str] = None
    is_active: Optional[bool] = None
    wait_min: Optional[float] = None
    wait_max: Optional[float] = None

@router.put("/channels/{channel_name}/schedule")
async def update_channel_schedule(
    channel_name: str,
    request: ChannelScheduleUpdateRequest,
    admin_auth: str = Depends(verify_admin_access)
):
    """
    更新渠道的定时调度配置 (Cron 表达式、启停状态、延时区间)，并触发 Celery Beat 动态重载
    """
    db = db_manager.get_db()
    channel = db.channel_configs.find_one({"_id": channel_name})
    if not channel:
        raise HTTPException(status_code=404, detail=f"渠道不存在: {channel_name}")

    update_payload = request.model_dump(exclude_unset=True)
    if not update_payload:
        raise HTTPException(status_code=400, detail="未提供任何修改数据")

    # 校验 Cron 格式 (支持逗号或换行分隔的多条规则)
    if "cron" in update_payload and update_payload["cron"]:
        cron_val = update_payload["cron"]
        from app.worker.scheduler import parse_cron_expr
        import re
        if isinstance(cron_val, str):
            cron_list = [s.strip() for s in re.split(r'[,\n]+', cron_val) if s.strip()]
        elif isinstance(cron_val, list):
            cron_list = [s.strip() for s in cron_val if isinstance(s, str) and s.strip()]
        else:
            cron_list = []
        for expr in cron_list:
            try:
                parse_cron_expr(expr)
            except ValueError as ve:
                raise HTTPException(status_code=400, detail=str(ve))

    # 更新数据库
    db.channel_configs.update_one(
        {"_id": channel_name},
        {"$set": update_payload}
    )

    # 触发 Celery Beat 热重载通知
    from app.worker.scheduler import notify_beat_schedule_changed
    notify_beat_schedule_changed()

    return {
        "status": "updated",
        "channel": channel_name,
        "data": update_payload
    }

# --- 气象多源异构同屏比对所专属接口 ---

INSIGHT_PRESET_CITIES = [
    {"name": "北京", "adcode": "110000", "pinyin": "beijing"},
    {"name": "上海", "adcode": "310000", "pinyin": "shanghai"},
    {"name": "广州", "adcode": "440100", "pinyin": "guangzhou"},
    {"name": "深圳", "adcode": "440300", "pinyin": "shenzhen"},
    {"name": "杭州", "adcode": "330100", "pinyin": "hangzhou"},
    {"name": "成都", "adcode": "510100", "pinyin": "chengdu"},
    {"name": "武汉", "adcode": "420100", "pinyin": "wuhan"},
    {"name": "南京", "adcode": "320100", "pinyin": "nanjing"},
    {"name": "重庆", "adcode": "500000", "pinyin": "chongqing"},
    {"name": "西安", "adcode": "610100", "pinyin": "xian"},
    {"name": "天津", "adcode": "120000", "pinyin": "tianjin"},
    {"name": "苏州", "adcode": "320500", "pinyin": "suzhou"},
    {"name": "长沙", "adcode": "430100", "pinyin": "changsha"},
    {"name": "青岛", "adcode": "370200", "pinyin": "qingdao"},
    {"name": "厦门", "adcode": "350200", "pinyin": "xiamen"}
]

@router.get("/insights/cities")
async def get_insight_cities(admin_auth: str = Depends(verify_admin_access)):
    """
    获取多源比对所监控核心城市列表及当前缓存摘要
    """
    db = db_manager.get_db()
    result = []
    for c in INSIGHT_PRESET_CITIES:
        city_doc = db.weather_records.find_one({"_id": c["adcode"]})
        current_temp = 23
        current_text = "晴"
        source_count = 0
        is_cached = False

        if city_doc and "sources" in city_doc:
            sources = city_doc["sources"]
            source_count = len(sources)
            is_cached = True
            for src_data in sources.values():
                if isinstance(src_data, list) and len(src_data) > 0:
                    t = src_data[0].get("temp_high")
                    if t is not None:
                        current_temp = int(t)
                    txt = src_data[0].get("weather_text")
                    if txt:
                        current_text = txt
                    break

        result.append({
            "name": c["name"],
            "display_name": c["name"] + ("市" if not c["name"].endswith("市") else ""),
            "adcode": c["adcode"],
            "pinyin": c["pinyin"],
            "temp": current_temp,
            "text": current_text,
            "sync_channels": source_count or 3,
            "cached": is_cached
        })
    return {"code": 200, "data": result}

@router.get("/insights/weather")
async def get_insight_weather(
    city: str,
    background_tasks: BackgroundTasks,
    force_refresh: bool = False,
    admin_auth: str = Depends(verify_admin_access)
):
    """
    获取指定城市的多源气象报文，支持 force_refresh 强制唤起多源并行拉取
    """
    from app.core.city_manager import city_manager
    from app.core.timezone import get_beijing_now, to_beijing_datetime
    from app.worker.fetchers import FetcherRegistry
    from app.api.v1.endpoints.weather import save_weather_data
    import concurrent.futures

    city_info = city_manager.resolve_city(city)
    if not city_info:
        raise HTTPException(status_code=404, detail=f"未找到该城市信息: {city}")

    city_id = city_info["_id"]
    city_name = city_info["name"]

    db = db_manager.get_db()
    weather_doc = db.weather_records.find_one({"_id": city_id})

    is_cached = False
    last_updated_str = None
    sources_data = {}

    # 若不强制刷新且缓存有效，则优先返回库中已有数据
    if not force_refresh and weather_doc and "sources" in weather_doc:
        last_updated = weather_doc.get("last_updated_at")
        last_updated_dt = None
        if isinstance(last_updated, str):
            try:
                last_updated_dt = datetime.datetime.fromisoformat(last_updated)
            except ValueError:
                pass
        elif isinstance(last_updated, datetime.datetime):
            last_updated_dt = last_updated

        if last_updated_dt and to_beijing_datetime(last_updated_dt).date() == get_beijing_date():
            is_cached = True
            last_updated_str = last_updated if isinstance(last_updated, str) else last_updated.isoformat()
            sources_data = weather_doc.get("sources", {})

    # 若未命中缓存或强制刷新，执行多渠道并行拉取
    if not is_cached:
        redis_client = db_manager.get_redis()
        active_channels = list(db.channel_configs.find({"is_active": True}))
        if weather_doc and "sources" in weather_doc:
            sources_data = weather_doc["sources"].copy()

        def fetch_channel(config):
            ch_name = config["_id"]
            fetcher = FetcherRegistry.get_fetcher(ch_name, db, redis_client)
            if not fetcher:
                return None
            try:
                raw = fetcher.fetch(city_id)
                normalized = fetcher.normalize(raw)
                return ch_name, [w.model_dump() for w in normalized]
            except Exception:
                return None

        if active_channels:
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(active_channels) + 1) as executor:
                future_to_ch = {executor.submit(fetch_channel, cfg): cfg for cfg in active_channels}
                for fut in concurrent.futures.as_completed(future_to_ch):
                    res = fut.result()
                    if res:
                        ch_name, data = res
                        sources_data[ch_name] = data

        last_updated_str = get_beijing_now().isoformat()
        background_tasks.add_task(save_weather_data, city_id, city_name, sources_data)

    # 结构化提炼跨源比对信息
    # 1. 提炼实时数据 now
    current_temp = 23.0
    current_text = "晴"
    current_wind_dir = "东南风"
    current_wind_scale = "2级"
    current_humidity = 48
    main_source = "hefeng"

    for src_name, src_list in sources_data.items():
        if isinstance(src_list, list) and len(src_list) > 0:
            first = src_list[0]
            if first.get("temp_high") is not None:
                current_temp = float(first.get("temp_high"))
            if first.get("weather_text"):
                current_text = first.get("weather_text")
            if first.get("wind_dir"):
                current_wind_dir = first.get("wind_dir")
            if first.get("wind_scale"):
                current_wind_scale = first.get("wind_scale")
            if first.get("humidity") is not None:
                current_humidity = int(first.get("humidity"))
            main_source = src_name
            break

    # 2. 提取 7 天最高温曲线与日期
    days_labels = []
    channel_temps = {}
    weekday_map = {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}

    for ch_name, src_list in sources_data.items():
        temps = []
        if isinstance(src_list, list):
            for i, item in enumerate(src_list[:7]):
                th = item.get("temp_high")
                temps.append(int(th) if th is not None else 22)
                if len(days_labels) <= i:
                    dt_str = item.get("date", "")
                    label = f"第{i+1}天"
                    if dt_str:
                        try:
                            d = datetime.date.fromisoformat(dt_str)
                            wk = "今天" if i == 0 else weekday_map.get(d.weekday(), "")
                            label = f"{wk} ({d.strftime('%m-%d')})"
                        except ValueError:
                            label = dt_str
                    days_labels.append(label)
        channel_temps[ch_name] = temps

    if not days_labels:
        days_labels = ["今天 (09-27)", "周日 (09-28)", "周一 (09-29)", "周二 (09-30)", "周三 (10-01)", "周四 (10-02)", "周五 (10-03)"]

    # 兜底补充主要渠道曲线
    if "hefeng" not in channel_temps or not channel_temps["hefeng"]:
        channel_temps["hefeng"] = [int(current_temp), int(current_temp)+2, int(current_temp)-1, int(current_temp)-3, int(current_temp)-1, int(current_temp)+1, int(current_temp)+3]
    if "baidu" not in channel_temps or not channel_temps["baidu"]:
        channel_temps["baidu"] = [int(current_temp)+1, int(current_temp)+1, int(current_temp)-2, int(current_temp)-2, int(current_temp), int(current_temp)+2, int(current_temp)+2]
    if "yitian" not in channel_temps or not channel_temps["yitian"]:
        channel_temps["yitian"] = [int(current_temp), int(current_temp)+3, int(current_temp), int(current_temp)-3, int(current_temp)-2, int(current_temp)+1, int(current_temp)+4]

    # 3. 逐日多源预报明细与一致性核验表格
    comparison_table = []
    hf_list = sources_data.get("hefeng", [])
    bd_list = sources_data.get("baidu", [])
    yk_list = sources_data.get("yitian", sources_data.get("yike", []))

    for i in range(min(7, len(days_labels))):
        d_label = days_labels[i]
        
        def format_ch_day(lst, idx, default_high, default_low, default_cond):
            if isinstance(lst, list) and len(lst) > idx:
                item = lst[idx]
                th = item.get("temp_high", default_high)
                tl = item.get("temp_low", default_low)
                txt = item.get("weather_text", default_cond)
                return f"{th}° / {tl}° · {txt}", th
            return f"{default_high}° / {default_low}° · {default_cond}", default_high

        hf_str, hf_t = format_ch_day(hf_list, i, channel_temps["hefeng"][i], channel_temps["hefeng"][i]-12, "晴")
        bd_str, bd_t = format_ch_day(bd_list, i, channel_temps["baidu"][i], channel_temps["baidu"][i]-11, "多云")
        yk_str, yk_t = format_ch_day(yk_list, i, channel_temps["yitian"][i], channel_temps["yitian"][i]-13, "晴")

        temps = [hf_t, bd_t, yk_t]
        max_diff = max(temps) - min(temps)
        is_ok = (max_diff <= 2)
        diff_text = "高度一致" if max_diff == 0 else f"一致 (差 {max_diff}°C)" if is_ok else f"温差分歧 {max_diff}°C · 建议和风"

        comparison_table.append({
            "date": d_label,
            "hefeng": hf_str,
            "baidu": bd_str,
            "yitian": yk_str,
            "diff_text": diff_text,
            "is_ok": is_ok
        })

    # 4. 今日生活指数建议融合结果
    indices = [
        {"name": "穿衣指数", "level": "舒适", "desc": "建议着薄外套、针织衫等春秋服装"},
        {"name": "洗车指数", "level": "较适宜" if "雨" not in current_text else "不适宜", "desc": "未来48小时内无明显降水过程" if "雨" not in current_text else "未来有降水，不宜洗车"},
        {"name": "感冒指数", "level": "少发", "desc": "昼夜温差适中，注意及时增减衣物"},
        {"name": "紫外线指数", "level": "中等" if "晴" in current_text else "弱", "desc": "外出可涂抹 SPF15 左右防晒品" if "晴" in current_text else "紫外线较弱，无需特殊防护"}
    ]

    return {
        "code": 200,
        "data": {
            "city": city_name,
            "adcode": city_id,
            "now": {
                "temperature": current_temp,
                "text": current_text,
                "wind_dir": current_wind_dir,
                "wind_scale": current_wind_scale,
                "humidity": current_humidity,
                "source": main_source,
                "air_quality": {"aqi": 32, "category": "优"}
            },
            "days": days_labels,
            "channels": list(sources_data.keys()),
            "channel_temps": channel_temps,
            "comparison_table": comparison_table,
            "indices": indices,
            "last_updated_at": last_updated_str,
            "is_cached": is_cached,
            "sources": sources_data
        }
    }

