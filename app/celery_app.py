from celery import Celery
from app.core.db import get_redis_uri, get_db


# 获取 Redis URI (直连配置)
redis_uri = get_redis_uri()

# 初始化 Celery 应用实例
# "weather_aggregator": Celery 应用的名称
celery_app = Celery(
    "weather_aggregator",
    broker=redis_uri,
    backend=redis_uri,
    include=['app.worker.tasks']  # 显式包含任务模块
)

# 更新 Celery 配置
celery_app.conf.update(
    task_serializer="json",       # 任务序列化格式为 JSON
    accept_content=["json"],      # 接受的内容类型为 JSON
    result_serializer="json",     # 结果序列化格式为 JSON
    timezone="Asia/Shanghai",     # 设置时区为上海时间
    enable_utc=True,              # 启用 UTC
    task_ignore_result=True,      # 忽略任务返回结果，避免在 Redis 中累积大量 celery-task-meta 临时无用键
    beat_scheduler="app.worker.scheduler.DynamicMongoScheduler",  # 启用支持动态重载的 MongoDB 调度器
)

from app.worker.scheduler import load_schedule_from_db

# 兼容保留函数名，调度由 DynamicMongoScheduler 运行时动态加载
load_beat_schedule = load_schedule_from_db
celery_app.conf.beat_schedule = {}

