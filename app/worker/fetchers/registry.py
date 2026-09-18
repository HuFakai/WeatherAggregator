from typing import Dict, Type, Optional, List
from app.worker.fetchers.base import BaseFetcher
from app.core.logger import logger

class FetcherRegistry:
    """
    数据源抓取器注册中心与工厂
    提供统一的渠道注册与获取接口，解耦具体 Fetcher 实现
    """
    _registry: Dict[str, Type[BaseFetcher]] = {}

    @classmethod
    def register(cls, channel_name: str):
        """
        类装饰器：注册 Fetcher 渠道实现
        例如:
            @FetcherRegistry.register("baidu")
            class BaiduFetcher(BaseFetcher):
                ...
        """
        def decorator(subclass: Type[BaseFetcher]):
            cls._registry[channel_name] = subclass
            return subclass
        return decorator

    @classmethod
    def get_fetcher(
        cls, 
        channel_name: str, 
        db=None, 
        redis_client=None
    ) -> Optional[BaseFetcher]:
        """
        获取指定渠道的 Fetcher 实例
        
        参数:
            channel_name: 渠道标识 (如 'baidu', 'yiketianqi', 'hefeng')
            db: 可选的 MongoDB 实例，未提供时自动获取
            redis_client: 可选的 Redis 实例，未提供时自动获取
            
        返回:
            BaseFetcher 实例或 None (若渠道未注册)
        """
        fetcher_cls = cls._registry.get(channel_name)
        if not fetcher_cls:
            logger.warning(f"未找到已注册的抓取器渠道: {channel_name}")
            return None

        from app.core.db import get_db, get_redis_client
        from app.core.key_manager import KeyManager

        _db = db if db is not None else get_db()
        _redis = redis_client if redis_client is not None else get_redis_client()
        key_manager = KeyManager(_db, _redis)

        return fetcher_cls(key_manager)

    @classmethod
    def get_fetcher_class(cls, channel_name: str) -> Optional[Type[BaseFetcher]]:
        """
        获取指定渠道的 Fetcher 类
        """
        return cls._registry.get(channel_name)

    @classmethod
    def list_supported_channels(cls) -> List[str]:
        """
        获取所有已注册的渠道列表
        """
        return list(cls._registry.keys())

