from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    embedding_model: str = "gemini-embedding-2"
    jwt_secret: str = "change-me-in-production"
    database_url: str = "sqlite:///./sos.db"
    upload_dir: str = "uploads"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_enabled: bool = False

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
