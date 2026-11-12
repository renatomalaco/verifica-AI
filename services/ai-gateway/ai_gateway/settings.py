from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Triage model: 'fake', 'jev' or 'gemini' (reuses the GEMINI_* settings).
    AI_PROVIDER: str = "fake"
    JEV_BASE_URL: str = "https://api.typesafe.ai"
    JEV_API_KEY: str = ""
    JEV_TIMEOUT_SECONDS: float = 1.5
    EXPLAIN_PROVIDER: str = "fake"  # 'fake' or 'gemini'
    GEMINI_API_KEY: str = ""
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com"
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_TIMEOUT_SECONDS: float = 8.0
    # Single source of truth for logo embeddings: embedder, catalog and pgvector column (R4)
    # must agree.
    EMBEDDING_DIM: int = 768
    SIGLIP_MODEL: str = "google/siglip-base-patch16-224"
    # Commit of SIGLIP_MODEL on the Hugging Face Hub: pinned so a moved branch cannot swap
    # the weights. Change both together, and keep the Dockerfile ARGs in sync.
    SIGLIP_REVISION: str = "7fd15f0689c79d79e38b1c2e2e2370a7bf2761ed"
    # Postgres with the seeded marcas_referencias; without it Visual RAG answers 503.
    DATABASE_URL: str = ""
    BRAND_MATCH_THRESHOLD: float = 0.82
    # Starting point, not a measured value: calibrate both limits on the test split (Fβ, β = 2).
    BRAND_GRAY_ZONE_FLOOR: float = 0.70
    VLM_PROVIDER: str = "none"  # 'none' or 'gemini' (reuses the GEMINI_* settings)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
