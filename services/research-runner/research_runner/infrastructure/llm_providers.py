"""The real language models the study can call, configured exactly like ai-gateway."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from ai_gateway.infrastructure.gemini_triage_client import GeminiTriageClient
from ai_gateway.infrastructure.jev_client import HttpJevClient
from contracts import TriageResult

from research_runner.domain.pricing import TokenPrice
from research_runner.settings import ResearchSettings

# Takes the guarded envelope, returns the model's answer and what that call cost in USD.
ModelCall = Callable[[str], Awaitable[tuple[TriageResult, float]]]

GEMINI_PRICES = ("GEMINI_PRICE_INPUT_USD_PER_1M", "GEMINI_PRICE_OUTPUT_USD_PER_1M", "GEMINI_PRICE_DATE")
JEV_PRICES = ("JEV_PRICE_USD_PER_1K_CALLS", "JEV_PRICE_DATE")
JEV_MODEL = "jev-latest"  # the model HttpJevClient asks for


@dataclass(frozen=True)
class Provider:
    call: ModelCall
    description: dict[str, Any]  # provider, model, prices and price date, written into the report


@dataclass(frozen=True)
class StudyProviders:
    pure_vlm: Provider | None = None
    triage: Provider | None = None
    pure_vlm_missing: str = "GEMINI_API_KEY is not set"
    triage_missing: str = "AI_PROVIDER is not 'gemini' or 'jev'"
    pause_seconds: float = 0.0


def providers_from_settings(settings: ResearchSettings) -> StudyProviders:
    pure_vlm = _gemini(settings)
    triage = _triage(settings)
    return StudyProviders(
        pure_vlm=pure_vlm if isinstance(pure_vlm, Provider) else None,
        triage=triage if isinstance(triage, Provider) else None,
        pure_vlm_missing="" if isinstance(pure_vlm, Provider) else pure_vlm,
        triage_missing="" if isinstance(triage, Provider) else triage,
        pause_seconds=settings.RESEARCH_LLM_PAUSE_SECONDS,
    )


def _triage(settings: ResearchSettings) -> Provider | str:
    provider = settings.AI_PROVIDER.lower()
    if provider == "gemini":
        return _gemini(settings)
    if provider == "jev":
        return _jev(settings)
    return f"AI_PROVIDER is '{settings.AI_PROVIDER}', not 'gemini' or 'jev'"


def _gemini(settings: ResearchSettings) -> Provider | str:
    """A Provider, or why there is none (the report quotes it)."""
    if not settings.GEMINI_API_KEY:
        return "GEMINI_API_KEY is not set"
    missing = _unset(settings, GEMINI_PRICES)
    if missing:
        return f"{', '.join(missing)} not set: the cost could not be measured"

    client = GeminiTriageClient(
        base_url=settings.GEMINI_BASE_URL,
        api_key=settings.GEMINI_API_KEY,
        model=settings.GEMINI_MODEL,
        timeout_seconds=settings.GEMINI_TIMEOUT_SECONDS,
    )
    price = TokenPrice(settings.GEMINI_PRICE_INPUT_USD_PER_1M, settings.GEMINI_PRICE_OUTPUT_USD_PER_1M)

    async def call(envelope: str) -> tuple[TriageResult, float]:
        measured = await client.measure(envelope)
        return measured.result, price.cost(measured.input_tokens, measured.output_tokens)

    return Provider(call, {
        "provider": "gemini",
        "model": settings.GEMINI_MODEL,
        "input_usd_per_1m": price.input_usd_per_1m,
        "output_usd_per_1m": price.output_usd_per_1m,
        "price_date": settings.GEMINI_PRICE_DATE,
    })


def _jev(settings: ResearchSettings) -> Provider | str:
    if not settings.JEV_API_KEY:
        return "AI_PROVIDER is 'jev' but JEV_API_KEY is not set"
    missing = _unset(settings, JEV_PRICES)
    if missing:
        return f"{', '.join(missing)} not set: the cost could not be measured"

    client = HttpJevClient(
        base_url=settings.JEV_BASE_URL, api_key=settings.JEV_API_KEY, timeout_seconds=settings.JEV_TIMEOUT_SECONDS
    )
    per_call = settings.JEV_PRICE_USD_PER_1K_CALLS / 1000

    async def call(envelope: str) -> tuple[TriageResult, float]:
        return await client.classify(envelope), per_call

    return Provider(call, {
        "provider": "jev",
        "model": JEV_MODEL,
        "usd_per_1k_calls": settings.JEV_PRICE_USD_PER_1K_CALLS,
        "price_date": settings.JEV_PRICE_DATE,
    })


def _unset(settings: ResearchSettings, names: tuple[str, ...]) -> list[str]:
    return [name for name in names if getattr(settings, name) in (None, "")]
