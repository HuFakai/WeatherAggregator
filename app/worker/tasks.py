from celery import shared_task
from datetime import datetime
from zoneinfo import ZoneInfo
from pymongo import MongoClient
from redis import Redis
from app.celery_app import celery_app
from app.worker.fetchers import FetcherRegistry
from app.core.city_manager import CityManager
from app.core.db import get_db
from app.core.logger import logger

def get_fetcher(channel_name):
    return FetcherRegistry.get_fetcher(channel_name)

# 初始化 KeyManager 实例 (全局实例可能在 fork 后有问题，建议在任务内或 get_fetcher 内初始化)
# key_manager = RandomKeyManager(db, redis_client)
# 初始化 CityManager 实例 (移至任务内部)
# city_manager = CityManager(db)

@celery_app.task(name="update_city_weather")
def update_city_weather(city_identifier: str, channel_name: str):
    """
    Celery 异步任务: 更新指定城市和渠道的天气数据
    
    流程:
    1. 解析 city_identifier (可能是 adcode 或 城市名称) 获取标准 adcode
    2. 根据 channel_name 实例化对应的 Fetcher
    3. 调用 fetch 方法获取原始数据
    4. 调用 normalize 方法清洗数据
    5. 将清洗后的数据存入 MongoDB (Upsert 模式)
    
    参数:
        city_identifier: 城市标识符 (Adcode 如 '110105' 或 名称 如 '朝阳区')
        channel_name: 渠道名称 (如 'baidu')
    """
    logger.info(f"开始更新城市: {city_identifier}, 渠道: {channel_name}")
    
    # 1. 解析城市信息
    # 在任务内部初始化 CityManager，确保 DB 连接正确
    db = get_db()
    
    # 获取渠道配置以读取自定义等待时间
    # 默认等待时间: 1-3秒
    wait_min = 1
    wait_max = 3
    
    try:
        channel_config = db.channel_configs.find_one({"_id": channel_name})
        if channel_config:
            wait_min = channel_config.get("wait_min", 1)
            wait_max = channel_config.get("wait_max", 3)
    except Exception as e:
        logger.error(f"读取渠道配置失败: {e}")

    # 增加随机延时，避免并发过高触发 API 频率限制
    # 仅在 Celery 任务中生效，不影响 API 实时调用
    import time
    import random
    sleep_time = random.uniform(wait_min, wait_max)
    # logger.debug(f"[{channel_name}] 随机等待 {sleep_time:.2f}s (范围: {wait_min}-{wait_max}s)")
    time.sleep(sleep_time)

    city_manager = CityManager(db)
    city_info = city_manager.resolve_city(city_identifier)
    if not city_info:
        logger.warning(f"城市未找到: {city_identifier}")
        return

    adcode = city_info["_id"]
    logger.info(f"解析城市: {city_identifier} -> {adcode} ({city_info.get('name')})")

    # 2. 获取对应的 Fetcher
    fetcher = get_fetcher(channel_name)
    if not fetcher:
        logger.error(f"不支持的渠道: {channel_name}")
        return

    try:
        # 3. 抓取数据
        raw_data = fetcher.fetch(adcode)
        
        # 4. 标准化数据
        standard_weather_list = fetcher.normalize(raw_data)
        
        # 5. 存入 MongoDB
        db = get_db()
        collection = db.weather_records
        
        update_data = {
            f"sources.{channel_name}": [w.model_dump() for w in standard_weather_list],
            "last_updated_at":datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
            "city_name": city_info.get("name"),
            "adcode": adcode
        }
        
        result = collection.update_one(
            {"_id": adcode},
            {"$set": update_data},
            upsert=True
        )
        
        logger.info(f"更新成功 {adcode} ({city_info.get('name')}). 修改: {result.modified_count}, 插入: {result.upserted_id}")

    except Exception as e:
        logger.error(f"任务失败 {adcode}: {e}")

@celery_app.task(name="trigger_channel_update")
def trigger_channel_update(channel_name: str):
    """
    触发指定渠道的全量更新任务
    """
    logger.info(f"TRIGGER_START: 触发渠道更新: {channel_name}")
    
    try:
        db = get_db()
        # 获取所有启用的城市
        # 显式转换为列表以避免游标问题，并排序确保顺序一致
        cities = list(db.cities.find({"is_active": True}).sort("_id", 1))
        
        total_cities = len(cities)
        logger.info(f"[{channel_name}] 发现 {total_cities} 个启用城市")
        
        count = 0
        for city in cities:
            city_id = city["_id"]
            # 为每个城市触发一个 update_city_weather 任务
            # 使用 adcode 作为标识符
            # logger.debug(f"[{channel_name}] Dispatching {city_id}") # 调试用，生产环境可注释
            update_city_weather.delay(city_id, channel_name)
            count += 1
            
        logger.info(f"TRIGGER_END: 已触发 {count}/{total_cities} 个任务，渠道: {channel_name}")
    except Exception as e:
        logger.error(f"TRIGGER_ERROR: 触发渠道更新失败 {channel_name}: {e}")
        raise e
