from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    AI_PROVIDER: str = "fake"  # 'fake' or 'jev'
    JEV_BASE_URL: str = "https://api.typesafe.ai"
    JEV_API_KEY: str = ""
    JEV_TIMEOUT_SECONDS: float = 1.5
    EXPLAIN_PROVIDER: str = "fake"  # 'fake' or 'gemini'
    GEMINI_API_KEY: str = ""
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com"
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_TIMEOUT_SECONDS: float = 8.0
    # Single source of truth for logo embeddings: embedder, catalog and pgvector column (R4) must agree.
    EMBEDDING_DIM: int = 768

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
