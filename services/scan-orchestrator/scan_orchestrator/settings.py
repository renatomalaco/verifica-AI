from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    AI_GATEWAY_URL: str = "http://localhost:8001"
    URL_INSPECTOR_URL: str = "http://localhost:8002"
    IMAGE_EXTRACTOR_URL: str = "http://localhost:8003"
    REDIS_URL: str = "redis://localhost:6379/0"
    THRESHOLD_SCAM: float = 0.90
    THRESHOLD_SAFE: float = 0.10
    DATABASE_URL: str = ""
    # Per-IP flood guard on POST /api/v1/scans and /scans/stream (R7). Short window, so the
    # person can retry soon; generous, because mobile carriers put many people behind one IP.
    SCAN_IP_LIMIT: int = 20
    SCAN_IP_WINDOW_SECONDS: int = 60
    # Off until the brand catalog is seeded and the threshold calibrated (R4): an empty catalog
    # answers 503, and that failure would cap every inspected page at CUIDADO.
    VISUAL_RAG_ENABLED: bool = False

    # "Me explica" (R5b): per-device quota and per-IP cap.
    # The verdict and "o que fazer" never go through here.
    # Empty = random per-process secret (cookies are invalidated on every restart).
    DEVICE_TOKEN_SECRET: str = ""
    DEVICE_COOKIE_SECURE: bool = False  # True in production (HTTPS)
    EXPLAIN_DAILY_LIMIT: int = 3
    EXPLAIN_MONTHLY_LIMIT: int = 30
    EXPLAIN_IP_LIMIT: int = 30
    EXPLAIN_IP_WINDOW_SECONDS: int = 3600
    QUOTA_UTC_OFFSET_HOURS: int = -3  # Brasília, no daylight saving time since 2019

    # Research area sign-in (R5a). Keys are base64 raw Ed25519
    # (`python -m scan_orchestrator.research_cli keygen`).
    # Without them nobody signs in: protected routes answer 401 and login answers 503.
    AUTH_JWT_PRIVATE_KEY: str = ""
    AUTH_JWT_PUBLIC_KEY: str = ""
    AUTH_COOKIE_SECURE: bool = True
    AUTH_ALLOWED_ORIGINS: Annotated[list[str], NoDecode] = [
        "http://localhost:5173"
    ]  # comma-separated in the env
    LOGIN_ACCOUNT_LIMIT: int = 5
    LOGIN_IP_LIMIT: int = 20
    LOGIN_WINDOW_SECONDS: int = 900
    PUBLIC_BASE_URL: str = "http://localhost:5173"  # where invite links point

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("AUTH_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value
