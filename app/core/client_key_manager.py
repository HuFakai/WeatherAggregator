import uuid
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from app.core.db import db_manager
from app.models.client_key import ClientKey
from app.core.timezone import get_beijing_now, get_beijing_today_str
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
            created_at=get_beijing_now()
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
            
            # 清理 Redis 统计数据 (按北京时间清理)
            try:
                today = get_beijing_now()
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

    def update_key(self, key: str, data: dict, new_key: Optional[str] = None) -> tuple[bool, str]:
        """
        更新密钥配置，支持修改密钥字符串并迁移 Redis 统计数据
        """
        doc = self.db[self.COLLECTION].find_one({"key": key})
        if not doc:
            return False, "原密钥不存在"

        update_payload = data.copy()

        # 如果需要修改密钥值
        if new_key and new_key != key:
            # 校验新 key 是否已被占用
            existing = self.db[self.COLLECTION].find_one({"key": new_key})
            if existing:
                return False, f"密钥 '{new_key}' 已存在，请使用其他值"
            update_payload["key"] = new_key

        if not update_payload:
            return True, ""

        result = self.db[self.COLLECTION].update_one(
            {"key": key},
            {"$set": update_payload}
        )

        if result.matched_count == 0:
            return False, "密钥更新失败"

        # 若修改了 key，迁移 Redis 中的调用统计
        if new_key and new_key != key:
            try:
                today = get_beijing_now()
                read_pipe = self.redis.pipeline()
                dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(self.STATS_RETENTION_DAYS + 1)]
                for d in dates:
                    old_k = f"{self.STATS_PREFIX}:{key}:{d}"
                    read_pipe.get(old_k)
                    read_pipe.ttl(old_k)
                res = read_pipe.execute()

                write_pipe = self.redis.pipeline()
                for idx, d in enumerate(dates):
                    val = res[idx * 2]
                    ttl = res[idx * 2 + 1]
                    if val is not None:
                        new_k = f"{self.STATS_PREFIX}:{new_key}:{d}"
                        old_k = f"{self.STATS_PREFIX}:{key}:{d}"
                        exp = ttl if ttl > 0 else 86400 * self.STATS_RETENTION_DAYS
                        write_pipe.setex(new_k, exp, val)
                        write_pipe.delete(old_k)
                write_pipe.execute()
                logger.info(f"成功将客户端密钥调用统计从 {key} 迁移至 {new_key}")
            except Exception as e:
                logger.error(f"迁移 Redis 统计失败 ({key} -> {new_key}): {e}")

        logger.info(f"Updated client key: {key} -> {new_key or key} with {data}")
        return True, ""

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
            # 使用简单的固定窗口计数 (基于北京时间当前分钟)
            current_minute = int(get_beijing_now().timestamp() // 60)
            rate_key = f"rate_limit:client:{key}:{current_minute}"
            
            # 使用 pipeline 保证 incr 与 expire 必然同时生效，彻底杜绝无 TTL 累积无用键
            pipe = self.redis.pipeline()
            pipe.incr(rate_key)
            pipe.expire(rate_key, 65)  # 1分钟后过期
            results = pipe.execute()
            current_count = results[0]
                
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
        记录调用次数 (Redis，按北京时间天切分)
        Key 格式: usage:client:{key}:{date_str}
        """
        today = get_beijing_today_str()
        redis_key = f"{self.STATS_PREFIX}:{key}:{today}"
        
        pipe = self.redis.pipeline()
        pipe.incr(redis_key)
        pipe.expire(redis_key, timedelta(days=self.STATS_RETENTION_DAYS))
        pipe.execute()

    def get_stats(self, key: str) -> Dict[str, int]:
        """
        获取最近 7 天的统计数据 (按北京时间回溯)
        """
        stats = {}
        today = get_beijing_now()
        
        for i in range(self.STATS_RETENTION_DAYS):
            date = today - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            redis_key = f"{self.STATS_PREFIX}:{key}:{date_str}"
            
            count = self.redis.get(redis_key)
            stats[date_str] = int(count) if count else 0
            
        return stats


client_key_manager = ClientKeyManager()
