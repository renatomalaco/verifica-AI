import logging
from functools import lru_cache
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import create_async_engine
from observability import configure_telemetry
from contracts import (
    TriageRequest,
    TriageResult,
    BrandMatchRequest,
    BrandMatchResult,
    ExplainRequest,
    ExplainResult,
)
from ai_gateway.settings import Settings
from ai_gateway.domain.envelope import guard_for_model
from ai_gateway.domain.brand_matcher import MatchPolicy
from ai_gateway.application.match_brand import (
    BrandCatalog,
    BrandVerifier,
    MatchBrandUseCase,
    VisualEmbedder,
)
from ai_gateway.infrastructure.pgvector_catalog import PgvectorBrandCatalog
from ai_gateway.infrastructure.siglip_embedder import SiglipEmbedder
from ai_gateway.infrastructure.gemini_brand_verifier import GeminiBrandVerifier
from ai_gateway.domain.triage import TriageClient
from ai_gateway.application.triage_with_reserve import TriageWithReserve
from ai_gateway.infrastructure.gemini_triage_client import GeminiTriageClient
from ai_gateway.infrastructure.fakes import FakeTriageClient
from ai_gateway.domain.explanation import ExplanationProvider
from ai_gateway.infrastructure.explanation_provider import (
    FakeExplanationProvider,
    GeminiExplanationProvider,
)

logger = logging.getLogger("ai_gateway.api")

app = FastAPI(title="ai-gateway", version="0.1.0")
configure_telemetry("ai-gateway", app)


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_visual_embedder(settings: Settings = Depends(get_settings)) -> VisualEmbedder:
    return _siglip(settings.SIGLIP_MODEL, settings.SIGLIP_REVISION, settings.EMBEDDING_DIM)


@lru_cache
def _siglip(model_name: str, revision: str, dimension: int) -> SiglipEmbedder:
    # One model in memory per process; it loads on the first request.
    return SiglipEmbedder(model_name=model_name, revision=revision, dimension=dimension)


def get_brand_catalog(settings: Settings = Depends(get_settings)) -> BrandCatalog:
    if not settings.DATABASE_URL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Visual RAG is not configured."
        )
    return _pgvector_catalog(settings.DATABASE_URL)


@lru_cache
def _pgvector_catalog(database_url: str) -> PgvectorBrandCatalog:
    # One engine (and connection pool) per process, not per request.
    return PgvectorBrandCatalog(create_async_engine(database_url, pool_pre_ping=True))


def get_brand_verifier(settings: Settings = Depends(get_settings)) -> BrandVerifier | None:
    if settings.VLM_PROVIDER.lower() != "gemini" or not settings.GEMINI_API_KEY:
        return None
    return GeminiBrandVerifier(
        base_url=settings.GEMINI_BASE_URL,
        api_key=settings.GEMINI_API_KEY,
        model=settings.GEMINI_MODEL,
        timeout_seconds=settings.GEMINI_TIMEOUT_SECONDS,
    )


def get_match_brand(
    settings: Settings = Depends(get_settings),
    embedder: VisualEmbedder = Depends(get_visual_embedder),
    catalog: BrandCatalog = Depends(get_brand_catalog),
    verifier: BrandVerifier | None = Depends(get_brand_verifier),
) -> MatchBrandUseCase:
    return MatchBrandUseCase(
        embedder=embedder,
        catalog=catalog,
        policy=MatchPolicy(
            threshold=settings.BRAND_MATCH_THRESHOLD, gray_floor=settings.BRAND_GRAY_ZONE_FLOOR
        ),
        dimension=settings.EMBEDDING_DIM,
        verifier=verifier,
    )


def _triage_on_gemini(settings: Settings) -> bool:
    return settings.AI_PROVIDER.lower() == "gemini" and bool(settings.GEMINI_API_KEY)


def _gemini_triage(settings: Settings, model: str, timeout_seconds: float) -> GeminiTriageClient:
    return GeminiTriageClient(
        base_url=settings.GEMINI_BASE_URL,
        api_key=settings.GEMINI_API_KEY,
        model=model,
        timeout_seconds=timeout_seconds,
    )


def _with_reserve(settings: Settings, primary: TriageClient) -> TriageClient:
    # The reserve is a light model: on the free tier it stays up when bigger ones answer 503.
    if not settings.GEMINI_FALLBACK_MODEL:
        return primary
    reserve = _gemini_triage(
        settings, settings.GEMINI_FALLBACK_MODEL, settings.GEMINI_TRIAGE_TIMEOUT_SECONDS
    )
    return TriageWithReserve(primary, reserve)


def get_triage_client(settings: Settings = Depends(get_settings)) -> TriageClient:
    if not _triage_on_gemini(settings):
        return FakeTriageClient()
    quick = _gemini_triage(settings, settings.GEMINI_MODEL, settings.GEMINI_TRIAGE_TIMEOUT_SECONDS)
    return _with_reserve(settings, quick)


def get_deep_triage_client(settings: Settings = Depends(get_settings)) -> TriageClient:
    if not _triage_on_gemini(settings):
        return FakeTriageClient()
    deep = _gemini_triage(
        settings, settings.GEMINI_DEEP_MODEL, settings.GEMINI_DEEP_TIMEOUT_SECONDS
    )
    return _with_reserve(settings, deep)


def get_explanation_provider(settings: Settings = Depends(get_settings)) -> ExplanationProvider:
    if settings.EXPLAIN_PROVIDER.lower() == "gemini" and settings.GEMINI_API_KEY:
        return GeminiExplanationProvider(
            base_url=settings.GEMINI_BASE_URL,
            api_key=settings.GEMINI_API_KEY,
            model=settings.GEMINI_MODEL,
            timeout_seconds=settings.GEMINI_TIMEOUT_SECONDS,
        )
    return FakeExplanationProvider()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ai-gateway"}


@app.post("/v1/triage", response_model=TriageResult)
async def triage(
    request: TriageRequest,
    triage_client: TriageClient = Depends(get_triage_client),
):
    return await _classify(triage_client, request.text)


@app.post("/v1/triage/deep", response_model=TriageResult)
async def deep_triage(
    request: TriageRequest,
    triage_client: TriageClient = Depends(get_deep_triage_client),
):
    return await _classify(triage_client, request.text)


async def _classify(triage_client: TriageClient, text: str) -> TriageResult:
    # PII is masked (LGPD) and the text wrapped in the anti-prompt-injection envelope
    # before reaching the model.
    try:
        return await triage_client.classify(guard_for_model(text))
    except RuntimeError as exc:
        # The reason only, never the text: the orchestrator turns the 503 into INCONCLUSIVO.
        logger.warning("triage model unavailable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Triage unavailable right now."
        ) from exc


@app.post("/v1/brand-match", response_model=BrandMatchResult)
async def match_brand(
    request: BrandMatchRequest,
    use_case: MatchBrandUseCase = Depends(get_match_brand),
) -> BrandMatchResult:
    # An empty catalog or a missing model is a failure, never "no brand found".
    try:
        return await use_case.run(request)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Visual RAG unavailable right now.",
        ) from exc


@app.post("/v1/explain", response_model=ExplainResult)
async def explain(
    request: ExplainRequest,
    provider: ExplanationProvider = Depends(get_explanation_provider),
) -> ExplainResult:
    # Receives only the precomputed verdict; the raw content never reaches this point (LGPD).
    try:
        return await provider.explain(request)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Explanation unavailable right now."
        ) from exc
