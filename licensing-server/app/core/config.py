from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "Licensing Server"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "sqlite:///./licensing.db"
    
    # Security
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ALGORITHM: str = "HS256"
    LICENSE_TOKEN_EXPIRE_DAYS: int = 365
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # License Limits
    FREE_TIER_DOCS_PER_MONTH: int = 100
    PRO_TIER_DOCS_PER_MONTH: int = 1000
    ENTERPRISE_TIER_DOCS_PER_MONTH: int = -1  # Unlimited
    
    class Config:
        env_file = ".env"


settings = Settings()
