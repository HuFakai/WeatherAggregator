import uuid
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from app.core.db import db_manager
from app.models.client_key import ClientKey
from app.core.logger import logger

class ClientKeyManager:
    """
    客户端密钥管理器
    负责密钥的 CRUD 和 Redis 统计
    """
    COLLECTION = "client_keys"
    STATS_PREFIX = "usage:client"
    STATS_RETENTION_DAYS = 7

    def __init__(self):
        self.db = db_manager.get_db()
        self.redis = db_manager.get_redis()

    def create_key(self, name: str) -> ClientKey:
        """
        创建新密钥
        """
        # 生成唯一 Key (简单起见使用 UUID，实际可更复杂)
        key_str = f"ck_{uuid.uuid4().hex[:16]}"
        
        client_key = ClientKey(
            key=key_str,
            name=name,
            created_at=datetime.now()
        )
        
        self.db[self.COLLECTION].insert_one(client_key.model_dump())
        logger.info(f"Created new client key: {name} ({key_str})")
        return client_key

    def delete_key(self, key: str) -> bool:
        """
        删除密钥
        """
        result = self.db[self.COLLECTION].delete_one({"key": key})
        if result.deleted_count > 0:
            logger.info(f"Deleted client key: {key}")
            
            # 清理 Redis 统计数据
            try:
                today = datetime.now()
                pipe = self.redis.pipeline()
                for i in range(self.STATS_RETENTION_DAYS + 1): # 多清理一天以防万一
                    date = today - timedelta(days=i)
                    date_str = date.strftime("%Y-%m-%d")
                    redis_key = f"{self.STATS_PREFIX}:{key}:{date_str}"
                    pipe.delete(redis_key)
                pipe.execute()
                logger.info(f"Cleaned up Redis stats for client key: {key}")
            except Exception as e:
                logger.error(f"Failed to clean up Redis stats for {key}: {e}")
                
            return True
        return False

    def update_key(self, key: str, data: dict) -> bool:
        """
        更新密钥配置
        """
        result = self.db[self.COLLECTION].update_one(
            {"key": key},
            {"$set": data}
        )
        if result.matched_count > 0:
            logger.info(f"Updated client key: {key} with {data}")
            return True
        return False

    def validate_access(self, key: str, ip: str) -> tuple[bool, str]:
        """
        验证访问权限 (Key有效性 + IP白名单 + 速率限制)
        Return: (is_valid, error_message)
        """
        doc = self.db[self.COLLECTION].find_one({"key": key})
        if not doc:
            return False, "Invalid API Key"
            
        client_key = ClientKey(**doc)
        
        # 1. IP 白名单检查
        if client_key.ip_whitelist_enabled:
            if ip not in client_key.ip_whitelist:
                # TODO: 支持 CIDR 解析 (目前仅支持精确匹配)
                logger.warning(f"IP {ip} blocked for key {key}")
                return False, "IP not allowed"

        # 2. QPM 速率限制
        if client_key.qpm_limit > 0:
            # Redis Key: rate_limit:client:{key}:{minute_timestamp}
            # 使用简单的固定窗口计数
            current_minute = int(datetime.now().timestamp() // 60)
            rate_key = f"rate_limit:client:{key}:{current_minute}"
            
            current_count = self.redis.incr(rate_key)
            if current_count == 1:
                self.redis.expire(rate_key, 65) # 1分钟后过期
                
            if current_count > client_key.qpm_limit:
                logger.warning(f"Rate limit exceeded for key {key} (Limit: {client_key.qpm_limit}, Current: {current_count})")
                return False, "Rate limit exceeded"

        return True, ""

    def list_keys(self) -> List[ClientKey]:
        """
        列出所有密钥
        """
        cursor = self.db[self.COLLECTION].find().sort("created_at", -1)
        return [ClientKey(**doc) for doc in cursor]

    def track_usage(self, key: str):
        """
        记录调用次数 (Redis)
        Key 格式: usage:client:{key}:{date_str}
        """
        today = datetime.now().strftime("%Y-%m-%d")
        redis_key = f"{self.STATS_PREFIX}:{key}:{today}"
        
        pipe = self.redis.pipeline()
        pipe.incr(redis_key)
        pipe.expire(redis_key, timedelta(days=self.STATS_RETENTION_DAYS))
        pipe.execute()

    def get_stats(self, key: str) -> Dict[str, int]:
        """
        获取最近 7 天的统计数据
        """
        stats = {}
        today = datetime.now()
        
        for i in range(self.STATS_RETENTION_DAYS):
            date = today - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            redis_key = f"{self.STATS_PREFIX}:{key}:{date_str}"
            
            count = self.redis.get(redis_key)
            stats[date_str] = int(count) if count else 0
            
        return stats

client_key_manager = ClientKeyManager()
