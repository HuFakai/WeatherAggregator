import random
from typing import Optional, List, Dict
from pymongo.database import Database
from redis import Redis
from datetime import datetime
from app.core.logger import logger

class KeyManager: # Renamed from RandomKeyManager to generic KeyManager if preferred, but keeping class name for compatibility
    """
    Key 管理器
    负责管理多渠道 API Key 的负载均衡、限流检查、故障屏蔽及统计
    """
    
    def __init__(self, mongo_db: Database, redis_client: Redis):
        self.db = mongo_db
        self.redis = redis_client

    def get_key(self, channel_name: str) -> Optional[str]:
        """
        获取一个可用的 API Key
        """
        # 1. 从 MongoDB 读取渠道配置
        config = self.db.channel_configs.find_one({"_id": channel_name})
        if not config or "keys_pool" not in config:
            logger.warning(f"[{channel_name}] 未找到配置或 keys_pool")
            return None

        keys_pool: List[Dict] = config["keys_pool"]
        valid_keys = []

        for key_info in keys_pool:
            key = key_info.get("key")
            daily_limit = key_info.get("daily_limit", 0)
            status = key_info.get("status")

            # 2. 过滤掉非 active 状态的 Key
            if status != "active":
                continue

            # 3. 检查 Redis 中是否被标记为 invalid
            invalid_key = f"weather:invalid:{channel_name}:{key}"
            if self.redis.exists(invalid_key):
                continue

            # 4. 检查 Redis 中是否超过每日限额
            # 直接检查今日统计数据，实现每日自动重置
            today = datetime.now().strftime("%Y-%m-%d")
            usage_key = f"stats:usage:{channel_name}:{today}"
            current_usage = self.redis.hget(usage_key, key)
            
            if current_usage and int(current_usage) >= daily_limit:
                # logger.debug(f"[{channel_name}] Key {key} 已达今日限额 ({current_usage}/{daily_limit})")
                continue

            valid_keys.append(key)

        if not valid_keys:
            logger.warning(f"[{channel_name}] 无可用 Key")
            return None

        # 5. 随机选择一个 Key
        selected_key = random.choice(valid_keys)
        
        # 6. 记录使用统计 (调用次数)
        self.record_usage(channel_name, selected_key)
        
        return selected_key

    def record_usage(self, channel_name: str, key: str):
        """
        记录 Key 的每日调用次数
        保留 3 天数据
        Redis Key: stats:usage:{channel}:{date} -> Hash {key: count}
        """
        today = datetime.now().strftime("%Y-%m-%d")
        redis_key = f"stats:usage:{channel_name}:{today}"
        
        try:
            # 增加计数
            self.redis.hincrby(redis_key, key, 1)
            
            # 设置过期时间 (3天 = 3 * 24 * 3600 = 259200 秒)
            if self.redis.ttl(redis_key) == -1:
                self.redis.expire(redis_key, 259200)
                
        except Exception as e:
            logger.error(f"记录统计失败: {e}")

    def mark_invalid(self, channel_name: str, key: str, duration: int = 86400, until_midnight: bool = False):
        """
        将 Key 标记为失效
        
        参数:
            duration: 失效时长(秒)，默认 24 小时
            until_midnight: 是否失效直到当天午夜 (用于每日限额耗尽的情况)
        """
        invalid_key = f"weather:invalid:{channel_name}:{key}"
        
        if until_midnight:
            now = datetime.now()
            # 计算距离明天 00:00:00 的秒数
            tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() + 86400
            duration = int(tomorrow - now.timestamp())
            # 至少保留 60 秒，避免边界情况
            duration = max(duration, 60)
            
        try:
            self.redis.setex(invalid_key, duration, "1")
            logger.warning(f"[{channel_name}] Key {key} 已标记为失效，时长 {duration}s (直到午夜: {until_midnight})")
        except Exception as e:
            logger.error(f"标记 Key 失效失败: {e}")

    def delete_key_stats(self, channel_name: str, key: str):
        """
        清理 Key 的统计数据
        """
        try:
            today = datetime.now()
            pipe = self.redis.pipeline()
            # 统计数据保留3天，清理过去4天以防万一
            for i in range(4):
                date = today - timedelta(days=i)
                date_str = date.strftime("%Y-%m-%d")
                redis_key = f"stats:usage:{channel_name}:{date_str}"
                pipe.hdel(redis_key, key)
            
            # 同时清理 invalid 标记
            invalid_key = f"weather:invalid:{channel_name}:{key}"
            pipe.delete(invalid_key)
            
            pipe.execute()
            logger.info(f"[{channel_name}] Cleaned up Redis stats for key: {key}")
        except Exception as e:
            logger.error(f"[{channel_name}] Failed to clean up Redis stats for {key}: {e}")

# 兼容旧代码引用
RandomKeyManager = KeyManager
