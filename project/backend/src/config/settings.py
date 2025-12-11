import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Redis settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_TTL: int = int(os.getenv("REDIS_TTL", 86400))  # 24 часа

    # GitHub settings
    GITHUB_API_URL: str = "https://api.github.com"

    # App settings
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:8000")

    # Security
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "your-secret-key-change-in-production-12345")

    class Config:
        env_file = ".env"


settings = Settings()
