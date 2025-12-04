import time
from pymongo import MongoClient
from redis import Redis
from sshtunnel import SSHTunnelForwarder
from contextlib import contextmanager
from app.core.config import settings
from app.core.logger import logger

_mongo_tunnel = None
_redis_tunnel = None
_mongo_client = None
_redis_client = None

def get_mongo_uri(host, port):
    return f"mongodb://{settings.MONGO_USER}:{settings.MONGO_PASS}@{host}:{port}/{settings.AUTH_DB}?authSource={settings.AUTH_DB}"

def get_redis_uri_str(host, port):
    return f"redis://:{settings.REDIS_PASS}@{host}:{port}/0"

def start_mongo_tunnel():
    """
    启动或获取活跃的 MongoDB SSH 隧道
    """
    global _mongo_tunnel
    
    if _mongo_tunnel and _mongo_tunnel.is_active:
        return _mongo_tunnel
        
    # 如果存在但不活跃，先停止
    if _mongo_tunnel:
        try:
            _mongo_tunnel.stop()
        except:
            pass
            
    logger.info(f"正在启动 MongoDB SSH 隧道至 {settings.SSH_HOST}...")
    try:
        _mongo_tunnel = SSHTunnelForwarder(
            (settings.SSH_HOST, settings.SSH_PORT),
            ssh_username=settings.SSH_USER,
            ssh_password=settings.SSH_PASS,
            remote_bind_address=(settings.MONGO_HOST, settings.MONGO_PORT)
        )
        _mongo_tunnel.start()
        logger.info(f"MongoDB SSH 隧道已建立。本地端口: {_mongo_tunnel.local_bind_port}")
        return _mongo_tunnel
    except Exception as e:
        logger.error(f"启动 MongoDB SSH 隧道失败: {e}")
        raise e

def start_redis_tunnel():
    """
    启动或获取活跃的 Redis SSH 隧道
    """
    global _redis_tunnel
    
    if _redis_tunnel and _redis_tunnel.is_active:
        return _redis_tunnel
        
    if _redis_tunnel:
        try:
            _redis_tunnel.stop()
        except:
            pass
            
    logger.info(f"正在启动 Redis SSH 隧道至 {settings.SSH_HOST}...")
    try:
        _redis_tunnel = SSHTunnelForwarder(
            (settings.SSH_HOST, settings.SSH_PORT),
            ssh_username=settings.SSH_USER,
            ssh_password=settings.SSH_PASS,
            remote_bind_address=(settings.REDIS_HOST, settings.REDIS_PORT)
        )
        _redis_tunnel.start()
        logger.info(f"Redis SSH 隧道已建立。本地端口: {_redis_tunnel.local_bind_port}")
        return _redis_tunnel
    except Exception as e:
        logger.error(f"启动 Redis SSH 隧道失败: {e}")
        raise e

def get_db_client():
    """
    获取 MongoDB 客户端 (单例模式)
    """
    global _mongo_client
    
    # 检查现有连接是否可用 (可选: ping)
    if _mongo_client:
        return _mongo_client

    if settings.APP_ENV == "local":
        tunnel = start_mongo_tunnel()
        local_port = tunnel.local_bind_port
        uri = get_mongo_uri("127.0.0.1", local_port)
    else:
        uri = get_mongo_uri(settings.MONGO_HOST, settings.MONGO_PORT)

    logger.info(f"正在连接 MongoDB: {uri.split('@')[-1]}")
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

    if settings.APP_ENV == "local":
        tunnel = start_redis_tunnel()
        local_port = tunnel.local_bind_port
        host = "127.0.0.1"
        port = local_port
    else:
        host = settings.REDIS_HOST
        port = settings.REDIS_PORT

    logger.info(f"正在连接 Redis: {host}:{port}")
    _redis_client = Redis(
        host=host, 
        port=port, 
        password=settings.REDIS_PASS, 
        db=0,
        max_connections=settings.REDIS_MAX_CONNECTIONS
    )
    return _redis_client

def get_redis_uri():
    """
    获取 Redis URI (用于 Celery)
    """
    if settings.APP_ENV == "local":
        tunnel = start_redis_tunnel()
        local_port = tunnel.local_bind_port
        return get_redis_uri_str("127.0.0.1", local_port)
    else:
        return get_redis_uri_str(settings.REDIS_HOST, settings.REDIS_PORT)

def get_db():
    """
    获取数据库实例
    """
    client = get_db_client()
    return client[settings.MONGO_DB]

def close_db():
    """
    关闭数据库连接和 SSH 隧道
    """
    global _mongo_client, _redis_client, _mongo_tunnel, _redis_tunnel
    
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None
        logger.info("MongoDB 连接已关闭。")
    
    if _redis_client:
        _redis_client.close()
        _redis_client = None
        logger.info("Redis 连接已关闭。")
    
    if _mongo_tunnel:
        _mongo_tunnel.stop()
        _mongo_tunnel = None
        logger.info("MongoDB SSH 隧道已关闭。")

    if _redis_tunnel:
        _redis_tunnel.stop()
        _redis_tunnel = None
        logger.info("Redis SSH 隧道已关闭。")

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

