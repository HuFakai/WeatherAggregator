import time
from celery.beat import Scheduler
from celery.schedules import crontab
from app.core.db import get_db, get_redis_client
from app.core.logger import logger

RELOAD_FLAG_KEY = "weather:beat:reload_flag"

def parse_cron_expr(cron_expr: str):
    """
    解析 Cron 表达式 (分 时 日 月 周)
    返回 crontab 实例或抛出 ValueError
    """
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Cron 格式无效: '{cron_expr}' (必须包含 5 个由空格分隔的部分，如: 0 */3 * * *)")
    minute, hour, day_of_month, month_of_year, day_of_week = parts
    return crontab(
        minute=minute,
        hour=hour,
        day_of_month=day_of_month,
        month_of_year=month_of_year,
        day_of_week=day_of_week
    )

def load_schedule_from_db():
    """
    从 MongoDB 读取所有活跃渠道的 Cron 调度
    """
    try:
        db = get_db()
        configs = list(db.channel_configs.find({"is_active": True}))
        schedule = {}
        for config in configs:
            channel_name = config["_id"]
            cron_str = config.get("cron")
            if not cron_str:
                continue
            cron_list = cron_str if isinstance(cron_str, list) else [cron_str]
            for idx, expr in enumerate(cron_list):
                try:
                    ct = parse_cron_expr(expr)
                    task_name = f"update_{channel_name}"
                    if len(cron_list) > 1:
                        task_name = f"{task_name}_{idx}"
                    schedule[task_name] = {
                        "task": "trigger_channel_update",
                        "schedule": ct,
                        "args": (channel_name,)
                    }
                except Exception as err:
                    logger.error(f"[{channel_name}] 解析 Cron 表达式 '{expr}' 失败: {err}")
        return schedule
    except Exception as e:
        logger.error(f"从 MongoDB 读取渠道调度失败: {e}")
        return {}

def notify_beat_schedule_changed():
    """
    向 Redis 发送重载信号，通知 Celery Beat 调度器动态刷新
    """
    try:
        redis_client = get_redis_client()
        redis_client.set(RELOAD_FLAG_KEY, str(time.time()))
        logger.info("已向 Redis 发送 Beat 调度热重载信号")
    except Exception as e:
        logger.error(f"发送 Beat 调度热重载信号失败: {e}")

class DynamicMongoScheduler(Scheduler):
    """
    动态 MongoDB 定时调度器
    继承自 celery.beat.Scheduler，支持无需重启容器动态增删改 Cron 任务
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_reload_flag = None
        self._last_check_time = 0
        self._check_interval = 5  # 每 5 秒检测一次信号变化

    def setup_schedule(self):
        """
        初始化加载调度规则
        """
        self.install_default_entries(self.schedule)
        self.reload_schedule(initial=True)

    def reload_schedule(self, initial=False):
        """
        从数据库重新加载并热更新内存中的 schedule
        """
        new_schedule_dict = load_schedule_from_db()

        # 移除已停用或已删除的任务
        current_tasks = list(self.schedule.keys())
        for task_name in current_tasks:
            if task_name not in new_schedule_dict:
                del self.schedule[task_name]
                logger.info(f"动态调度器已移除停用任务: {task_name}")

        # 更新或新增任务
        self.update_from_dict(new_schedule_dict)
        logger.info(f"动态调度器{'初始化' if initial else '热重载'}完成，当前活跃任务: {list(self.schedule.keys())}")

    def tick(self, *args, **kwargs):
        """
        每次调度心跳检测信号并执行
        """
        now = time.time()
        if now - self._last_check_time >= self._check_interval:
            self._last_check_time = now
            try:
                redis_client = get_redis_client()
                flag = redis_client.get(RELOAD_FLAG_KEY)
                flag_str = flag.decode("utf-8") if isinstance(flag, bytes) else str(flag or "")
                if self._last_reload_flag is None:
                    self._last_reload_flag = flag_str
                elif flag_str != self._last_reload_flag:
                    logger.info(f"检测到调度更新信号: {flag_str}，正在热重载调度...")
                    self.reload_schedule()
                    self._last_reload_flag = flag_str
            except Exception as e:
                logger.warning(f"检查调度更新信号异常: {e}")

        return super().tick(*args, **kwargs)
