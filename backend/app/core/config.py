from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    database_pool_size: int = 5
    database_max_overflow: int = 5
    database_pool_timeout_seconds: int = 5
    database_pool_recycle_seconds: int = 300
    database_connect_timeout_seconds: int = 5
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    cors_origins: str = "http://localhost:3000"
    storage_root: str = "storage"
    max_upload_bytes: int = 10 * 1024 * 1024
    ai_provider: str = "local_hf"
    ai_model_id: str = "Qwen/Qwen2.5-3B-Instruct"
    ai_base_url: str = ""
    ai_request_timeout_seconds: int = 45
    email_provider: str = "smtp"
    google_client_id: str = ""
    google_client_secret: str = ""
    google_refresh_token: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    email_from: str = ""
    otp_expire_minutes: int = 10
    otp_max_attempts: int = 5
    otp_resend_cooldown_seconds: int = 60
    otp_hourly_limit: int = 5
    email_delivery_timeout_seconds: int = 8
    auth_slow_request_ms: int = 1000
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()
