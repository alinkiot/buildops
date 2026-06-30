"""应用配置：通过环境变量或 .env 覆盖。"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_", extra="ignore")

    # 基础
    PROJECT_NAME: str = "施工企业全流程运营托管数字化系统"
    API_PREFIX: str = "/api"
    DEBUG: bool = True

    # 数据库：默认 SQLite，可切换 postgresql+psycopg / mysql+pymysql
    DATABASE_URL: str = "sqlite:///./construction_mvp.db"

    # JWT
    SECRET_KEY: str = "change-me-in-production-a-very-long-random-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12  # 12 小时

    # 文件存储
    UPLOAD_DIR: str = "./uploads"

    # 第三方集成 provider 切换：mock（默认，不外发）/ 真实厂商代号
    SMS_PROVIDER: str = "mock"
    ESIGN_PROVIDER: str = "mock"
    OCR_PROVIDER: str = "mock"

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
