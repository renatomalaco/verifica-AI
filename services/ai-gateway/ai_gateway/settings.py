from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Triage model: 'fake' or 'gemini' (reuses the GEMINI_* settings).
    AI_PROVIDER: str = "fake"
    EXPLAIN_PROVIDER: str = "fake"  # 'fake' or 'gemini'
    GEMINI_API_KEY: str = ""
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com"
    # No default: a model name in the code outlives the model (gemini-2.5-flash now answers 404).
    # Quick model: triage, "Me explica" and the VLM.
    GEMINI_MODEL: str = ""
    # Optional reserve for the quick triage, tried once when GEMINI_MODEL fails.
    GEMINI_FALLBACK_MODEL: str = ""
    # Stronger model that confirms doubtful triages and every would-be SEGURO.
    GEMINI_DEEP_MODEL: str = ""
    # "Me explica" and the VLM. The orchestrator waits AI_GATEWAY_TIMEOUT_SECONDS (20 s).
    GEMINI_TIMEOUT_SECONDS: float = 15.0
    # Each triage call, quick or deep, plus the reserve fits the orchestrator's 20 s per call.
    # Flash-Lite answered in under 2 s; gemini-3.5-flash in 2.6 to 9.2 s on the VM.
    GEMINI_TRIAGE_TIMEOUT_SECONDS: float = 6.0
    GEMINI_DEEP_TIMEOUT_SECONDS: float = 10.0
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

    @model_validator(mode="after")
    def _gemini_needs_a_model(self) -> Self:
        # Fail at startup: an empty model turns every Gemini call into INCONCLUSIVO.
        providers = (self.AI_PROVIDER, self.EXPLAIN_PROVIDER, self.VLM_PROVIDER)
        uses_gemini = any(p.lower() == "gemini" for p in providers) and self.GEMINI_API_KEY
        if uses_gemini and not self.GEMINI_MODEL:
            raise ValueError("GEMINI_MODEL is required when a provider is gemini")
        # Without a deep model no triage could be confirmed, so nothing would ever be SEGURO.
        triage_on_gemini = self.AI_PROVIDER.lower() == "gemini" and self.GEMINI_API_KEY
        if triage_on_gemini and not self.GEMINI_DEEP_MODEL:
            raise ValueError("GEMINI_DEEP_MODEL is required when AI_PROVIDER is gemini")
        return self
