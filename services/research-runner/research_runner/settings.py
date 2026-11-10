from ai_gateway.settings import Settings
from pydantic import field_validator


class ResearchSettings(Settings):
    """ai-gateway's provider settings plus the list prices that turn measured usage into cost."""

    # Prices have no default: a cost is only reported when its source and date are declared.
    GEMINI_PRICE_INPUT_USD_PER_1M: float | None = None
    GEMINI_PRICE_OUTPUT_USD_PER_1M: float | None = None  # thinking tokens are billed at this price too
    GEMINI_PRICE_DATE: str = ""
    JEV_PRICE_USD_PER_1K_CALLS: float | None = None
    JEV_PRICE_DATE: str = ""
    # Seconds between model calls, outside the measured latency (free tiers allow few requests per minute).
    RESEARCH_LLM_PAUSE_SECONDS: float = 0.0

    @field_validator("GEMINI_PRICE_INPUT_USD_PER_1M", "GEMINI_PRICE_OUTPUT_USD_PER_1M", "JEV_PRICE_USD_PER_1K_CALLS", mode="before")
    @classmethod
    def _empty_is_unset(cls, value: object) -> object:
        # .env.example lists the prices with empty values.
        return None if value == "" else value
