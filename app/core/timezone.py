import os
import time
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

# 进程级校准本地时区为北京时间 (UTC+8)
os.environ["TZ"] = "Asia/Shanghai"
if hasattr(time, "tzset"):
    try:
        time.tzset()
    except Exception:
        pass

BEIJING_TZ = ZoneInfo("Asia/Shanghai")

def get_beijing_now() -> datetime:
    """
    获取当前北京时间 (带 Asia/Shanghai 时区感知)
    """
    return datetime.now(BEIJING_TZ)

def get_beijing_today_str() -> str:
    """
    获取当前北京时间的日期字符串 (YYYY-MM-DD)
    """
    return get_beijing_now().strftime("%Y-%m-%d")

def get_beijing_date() -> date:
    """
    获取当前北京时间的日期对象
    """
    return get_beijing_now().date()

def to_beijing_datetime(dt: datetime) -> datetime:
    """
    将任意 datetime 安全转换为北京时间
    若 dt 为 naive (无时区信息)，则默认视为北京时间赋予时区
    若 dt 为 aware (有时区信息)，则转换为北京时间对应时刻
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=BEIJING_TZ)
    return dt.astimezone(BEIJING_TZ)
