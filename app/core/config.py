from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App
    APP_ENV: str = "local"
    
    # SSH Tunnel
    SSH_HOST: str = "115.190.90.61"
    SSH_PORT: int = 22
    SSH_USER: str = "root"
    SSH_PASS: str = "FaKai970506//"
    
    # MongoDB
    MONGO_HOST: str = "127.0.0.1"
    MONGO_PORT: int = 27017
    MONGO_USER: str = "root"
    MONGO_PASS: str = "snkjcx970506"
    MONGO_DB: str = "weather_aggregator"
    AUTH_DB: str = "admin"
    MONGO_MIN_POOL_SIZE: int = 10
    MONGO_MAX_POOL_SIZE: int = 100
    
    # Redis
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_PASS: str = "redis_NfkaAksnkjcx"
    REDIS_MAX_CONNECTIONS: int = 100
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_RETENTION: str = "3 days"
    
    # Admin Security
    ADMIN_LOGIN_KEY: str = "admin123"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
