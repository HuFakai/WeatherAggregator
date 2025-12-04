from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class ClientKey(BaseModel):
    """
    客户端 API 密钥模型
    """
    key: str = Field(..., description="唯一的 API 密钥")
    name: str = Field(..., description="密钥名称/描述")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    
    # Security & Rate Limiting
    ip_whitelist_enabled: bool = Field(default=False, description="是否开启 IP 白名单")
    ip_whitelist: list[str] = Field(default_factory=list, description="允许的 IP 列表 (CIDR or Single IP)")
    qpm_limit: int = Field(default=0, description="每分钟请求限制 (0 表示不限制)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "key": "ck_1234567890",
                "name": "My Mobile App",
                "created_at": "2023-10-27T10:00:00"
            }
        }
