from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    AI_GATEWAY_URL: str = "http://localhost:8001"
    URL_INSPECTOR_URL: str = "http://localhost:8002"
    IMAGE_EXTRACTOR_URL: str = "http://localhost:8003"
    REDIS_URL: str = "redis://localhost:6379/0"
    THRESHOLD_SCAM: float = 0.90
    THRESHOLD_SAFE: float = 0.10
    DATABASE_URL: str = ""
    RATE_LIMIT_PER_MINUTE: str = "60/minute"

    # "Me explica" (R5b): per-device quota and per-IP cap. The verdict and "o que fazer" never go through here.
    DEVICE_TOKEN_SECRET: str = ""  # empty = random per-process secret (cookies are invalidated on every restart)
    DEVICE_COOKIE_SECURE: bool = False  # True in production (HTTPS)
    EXPLAIN_DAILY_LIMIT: int = 3
    EXPLAIN_MONTHLY_LIMIT: int = 30
    EXPLAIN_IP_LIMIT: int = 30
    EXPLAIN_IP_WINDOW_SECONDS: int = 3600
    QUOTA_UTC_OFFSET_HOURS: int = -3  # Brasília, no daylight saving time since 2019

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
