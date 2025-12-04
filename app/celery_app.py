from celery import Celery
from app.core.db import get_redis_uri

# 获取 Redis URI (自动处理 SSH 隧道)
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
)

from celery.schedules import crontab
from app.core.db import get_db

def load_beat_schedule():
    """
    从 MongoDB 加载定时任务配置
    """
    print("正在从 MongoDB 加载 Beat 调度...")
    try:
        # 获取数据库连接 (可能会启动 SSH 隧道)
        db = get_db()
        configs = db.channel_configs.find({"is_active": True})
        schedule = {}
        
        for config in configs:
            channel_name = config["_id"]
            cron_str = config.get("cron")
            
            if not cron_str:
                continue
                
            # 统一转为列表处理
            cron_list = cron_str if isinstance(cron_str, list) else [cron_str]
            
            for idx, cron_expr in enumerate(cron_list):
                # 解析 cron 表达式 (简单处理: 分 时 日 月 周)
                # 假设格式为 "0 */3 * * *" (分 时 日 月 周)
                try:
                    parts = cron_expr.split()
                    if len(parts) != 5:
                        print(f"[{channel_name}] Cron 格式无效: {cron_expr} (应为 5 部分)")
                        continue
                        
                    minute, hour, day_of_month, month_of_year, day_of_week = parts
                    
                    # 如果有多个表达式，任务名加后缀区分
                    task_name = f"update_{channel_name}"
                    if len(cron_list) > 1:
                        task_name = f"{task_name}_{idx}"
                    
                    schedule[task_name] = {
                        "task": "trigger_channel_update",
                        "schedule": crontab(
                            minute=minute,
                            hour=hour,
                            day_of_month=day_of_month,
                            month_of_year=month_of_year,
                            day_of_week=day_of_week
                        ),
                        "args": (channel_name,)
                    }
                    print(f"已加载调度 {task_name}: {cron_expr}")
                except Exception as e:
                    print(f"[{channel_name}] 解析 Cron 失败: {e}")
                
        return schedule
    except Exception as e:
        print(f"加载 Beat 调度失败: {e}")
        return {}

# 加载定时任务
# 注意: 这会在 Celery 启动时执行
celery_app.conf.beat_schedule = load_beat_schedule()
