from fastapi import APIRouter, HTTPException, Depends, Header, Body
from typing import List, Dict, Optional
from app.core.db import db_manager
from app.core.config import settings
from app.core.client_key_manager import client_key_manager
from app.models.client_key import ClientKey
from pydantic import BaseModel
import datetime

router = APIRouter()

# Pydantic Models
class KeyAddRequest(BaseModel):
    key: str
    daily_limit: int = 2000
    desc: str = ""

# Admin Auth Dependency
async def verify_admin_access(x_admin_key: str = Header(..., alias="X-Admin-Key")):
    if x_admin_key != settings.ADMIN_LOGIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid Admin Key")
    return x_admin_key

@router.post("/login")
async def admin_login(key: str = Body(..., embed=True)):
    """
    验证管理密钥 (用于前端登录检查)
    """
    if key != settings.ADMIN_LOGIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid Key")
    return {"status": "ok"}

@router.get("/keys", response_model=List[Dict])
async def list_client_keys(admin_auth: str = Depends(verify_admin_access)):
    """
    获取所有客户端密钥及其统计信息
    """
    keys = client_key_manager.list_keys()
    result = []
    for k in keys:
        stats = client_key_manager.get_stats(k.key)
        # 计算总调用量 (7天)
        total_usage = sum(stats.values())
        
        key_data = k.model_dump()
        key_data["stats"] = stats
        key_data["total_usage_7d"] = total_usage
        result.append(key_data)
    return result

@router.post("/keys", response_model=ClientKey)
async def create_client_key(
    name: str = Body(..., embed=True),
    admin_auth: str = Depends(verify_admin_access)
):
    """
    创建新的客户端密钥
    """
    return client_key_manager.create_key(name)

@router.delete("/keys/{key}")
async def delete_client_key(
    key: str,
    admin_auth: str = Depends(verify_admin_access)
):
    """
    删除客户端密钥
    """
    success = client_key_manager.delete_key(key)
    if not success:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"status": "deleted"}

class KeyUpdateRequest(BaseModel):
    new_key: Optional[str] = None
    ip_whitelist_enabled: Optional[bool] = None
    ip_whitelist: Optional[List[str]] = None
    qpm_limit: Optional[int] = None

@router.put("/keys/{key}")
async def update_client_key(
    key: str,
    update_data: KeyUpdateRequest,
    admin_auth: str = Depends(verify_admin_access)
):
    """
    更新客户端密钥配置 (支持修改密钥值、IP白名单及QPM)
    """
    data = update_data.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No data provided")

    new_key = data.pop("new_key", None)
    if new_key is not None:
        new_key = new_key.strip()
        if not new_key:
            raise HTTPException(status_code=400, detail="密钥值不能为空")

    success, err_msg = client_key_manager.update_key(key, data, new_key=new_key)
    if not success:
        status_code = 404 if "原密钥不存在" in err_msg else 400
        raise HTTPException(status_code=status_code, detail=err_msg)
    return {"status": "updated", "key": new_key or key}

@router.get("/channels")
async def list_channels(admin_auth: str = Depends(verify_admin_access)):
    """
    获取所有渠道配置及状态
    """
    db = db_manager.get_db()
    redis = db_manager.get_redis()
    
    channels = list(db.channel_configs.find())
    
    # 获取 API Key 使用统计 (最近 3 天)
    today = datetime.date.today()
    dates = [(today - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(3)]
    
    for channel in channels:
        channel_name = channel["_id"]
        
        # 处理 keys_pool
        if "keys_pool" in channel:
            for key_info in channel["keys_pool"]:
                key = key_info.get("key")
                stats = {}
                total_3d = 0
                
                for date_str in dates:
                    # Redis Key: stats:usage:{channel}:{date} -> Hash {key: count}
                    redis_key = f"stats:usage:{channel_name}:{date_str}"
                    count = redis.hget(redis_key, key)
                    count_int = int(count) if count else 0
                    stats[date_str] = count_int
                    total_3d += count_int
                
                key_info["stats"] = stats
                key_info["total_3d"] = total_3d
        
    return channels

@router.post("/channels/{channel_name}/keys")
async def add_key(
    channel_name: str, 
    request: KeyAddRequest,
    admin_auth: str = Depends(verify_admin_access)
):
    """
    添加 API Key 到 keys_pool
    """
    db = db_manager.get_db()
    
    new_key = {
        "key": request.key,
        "status": "active",
        "daily_limit": request.daily_limit,
        "desc": request.desc
    }
    
    result = db.channel_configs.update_one(
        {"_id": channel_name},
        {"$push": {"keys_pool": new_key}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Channel not found")
    return {"status": "added", "key": request.key}

@router.delete("/channels/{channel_name}/keys")
async def remove_key(
    channel_name: str, 
    key: str = Body(..., embed=True),
    admin_auth: str = Depends(verify_admin_access)
):
    """
    从 keys_pool 删除 API Key
    """
    db = db_manager.get_db()
    result = db.channel_configs.update_one(
        {"_id": channel_name},
        {"$pull": {"keys_pool": {"key": key}}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Channel not found")
        
    # 清理 Redis 数据
    try:
        from app.core.key_manager import KeyManager
        redis = db_manager.get_redis()
        km = KeyManager(db, redis)
        km.delete_key_stats(channel_name, key)
    except Exception as e:
        # 不影响主流程
        print(f"Failed to cleanup redis stats: {e}")
        
    return {"status": "removed", "key": key}

@router.post("/channels/{channel_name}/update")
async def trigger_update(
    channel_name: str,
    admin_auth: str = Depends(verify_admin_access)
):
    """
    手动触发渠道全量更新
    """
    from app.worker.tasks import trigger_channel_update
    
    # 异步触发 Celery 任务
    trigger_channel_update.delay(channel_name)
    
    return {"status": "triggered", "message": f"Update task for {channel_name} started"}

class ChannelScheduleUpdateRequest(BaseModel):
    cron: Optional[str] = None
    is_active: Optional[bool] = None
    wait_min: Optional[float] = None
    wait_max: Optional[float] = None

@router.put("/channels/{channel_name}/schedule")
async def update_channel_schedule(
    channel_name: str,
    request: ChannelScheduleUpdateRequest,
    admin_auth: str = Depends(verify_admin_access)
):
    """
    更新渠道的定时调度配置 (Cron 表达式、启停状态、延时区间)，并触发 Celery Beat 动态重载
    """
    db = db_manager.get_db()
    channel = db.channel_configs.find_one({"_id": channel_name})
    if not channel:
        raise HTTPException(status_code=404, detail=f"渠道不存在: {channel_name}")

    update_payload = request.model_dump(exclude_unset=True)
    if not update_payload:
        raise HTTPException(status_code=400, detail="未提供任何修改数据")

    # 校验 Cron 格式
    if "cron" in update_payload and update_payload["cron"]:
        cron_val = update_payload["cron"]
        from app.worker.scheduler import parse_cron_expr
        cron_list = cron_val if isinstance(cron_val, list) else [cron_val]
        for expr in cron_list:
            try:
                parse_cron_expr(expr)
            except ValueError as ve:
                raise HTTPException(status_code=400, detail=str(ve))

    # 更新数据库
    db.channel_configs.update_one(
        {"_id": channel_name},
        {"$set": update_payload}
    )

    # 触发 Celery Beat 热重载通知
    from app.worker.scheduler import notify_beat_schedule_changed
    notify_beat_schedule_changed()

    return {
        "status": "updated",
        "channel": channel_name,
        "data": update_payload
    }
