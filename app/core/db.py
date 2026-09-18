from pymongo import MongoClient
from redis import Redis
from contextlib import contextmanager
from app.core.config import settings
from app.core.logger import logger

_mongo_client = None
_redis_client = None

def get_mongo_uri(host=None, port=None):
    h = host or settings.MONGO_HOST
    p = port or settings.MONGO_PORT
    return f"mongodb://{settings.MONGO_USER}:{settings.MONGO_PASS}@{h}:{p}/{settings.AUTH_DB}?authSource={settings.AUTH_DB}"

def get_redis_uri_str(host=None, port=None):
    h = host or settings.REDIS_HOST
    p = port or settings.REDIS_PORT
    return f"redis://:{settings.REDIS_PASS}@{h}:{p}/0"

def get_db_client():
    """
    获取 MongoDB 客户端 (单例模式)
    """
    global _mongo_client
    
    if _mongo_client:
        return _mongo_client

    uri = get_mongo_uri()
    logger.info(f"正在直接连接 MongoDB: {settings.MONGO_HOST}:{settings.MONGO_PORT}/{settings.MONGO_DB}")
    _mongo_client = MongoClient(
        uri,
        minPoolSize=settings.MONGO_MIN_POOL_SIZE,
        maxPoolSize=settings.MONGO_MAX_POOL_SIZE
    )
    return _mongo_client

def get_redis_client():
    """
    获取 Redis 客户端 (单例模式)
    """
    global _redis_client
    
    if _redis_client:
        return _redis_client

    logger.info(f"正在直接连接 Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    _redis_client = Redis(
        host=settings.REDIS_HOST, 
        port=settings.REDIS_PORT, 
        password=settings.REDIS_PASS, 
        db=0,
        max_connections=settings.REDIS_MAX_CONNECTIONS
    )
    return _redis_client

def get_redis_uri():
    """
    获取 Redis URI (用于 Celery)
    """
    return get_redis_uri_str()

def get_db():
    """
    获取数据库实例
    """
    client = get_db_client()
    return client[settings.MONGO_DB]

def close_db():
    """
    关闭数据库连接
    """
    global _mongo_client, _redis_client
    
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None
        logger.info("MongoDB 连接已关闭。")
    
    if _redis_client:
        _redis_client.close()
        _redis_client = None
        logger.info("Redis 连接已关闭。")

@contextmanager
def db_session():
    """
    上下文管理器，用于脚本或临时任务
    """
    try:
        yield get_db()
    finally:
        pass

class DBManager:
    """
    数据库管理器适配器
    """
    def get_db(self):
        return get_db()
        
    def get_redis(self):
        return get_redis_client()

db_manager = DBManager()

