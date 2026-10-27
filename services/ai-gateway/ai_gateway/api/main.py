from functools import lru_cache
from fastapi import FastAPI, Depends, HTTPException, status
from contracts import TriageRequest, TriageResult, BrandMatchRequest, BrandMatchResult, ExplainRequest, ExplainResult
from ai_gateway.settings import Settings
from ai_gateway.domain.sanitizer import sanitize_text
from ai_gateway.domain.data_masker import mask_pii
from ai_gateway.domain.envelope import build_envelope
from ai_gateway.domain.visual_embedder import VisualEmbedderProtocol, FakeVisualEmbedder
from ai_gateway.domain.brand_matcher import BrandMatcher, DefaultBrandCatalog
from ai_gateway.infrastructure.jev_client import JevClient, FakeJevClient, HttpJevClient
from ai_gateway.domain.explanation import ExplanationProvider
from ai_gateway.infrastructure.explanation_provider import FakeExplanationProvider, GeminiExplanationProvider

app = FastAPI(title="ai-gateway", version="0.1.0")

@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_visual_embedder(settings: Settings = Depends(get_settings)) -> VisualEmbedderProtocol:
    return FakeVisualEmbedder(dimension=settings.EMBEDDING_DIM)


def get_brand_matcher(settings: Settings = Depends(get_settings)) -> BrandMatcher:
    return BrandMatcher(catalog=_brand_catalog(settings.EMBEDDING_DIM), threshold=0.85)


@lru_cache
def _brand_catalog(dimension: int) -> DefaultBrandCatalog:
    return DefaultBrandCatalog(dimension=dimension)


def get_jev_client(settings: Settings = Depends(get_settings)) -> JevClient:
    if settings.AI_PROVIDER.lower() == "jev" and settings.JEV_API_KEY:
        return HttpJevClient(
            base_url=settings.JEV_BASE_URL,
            api_key=settings.JEV_API_KEY,
            timeout_seconds=settings.JEV_TIMEOUT_SECONDS,
        )
    return FakeJevClient()


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
    jev_client: JevClient = Depends(get_jev_client),
):
    # PII is masked (LGPD) and the text wrapped in the anti-prompt-injection envelope before reaching the model.
    envelope = build_envelope(mask_pii(sanitize_text(request.text)))
    return await jev_client.classify(envelope)


@app.post("/v1/brand-match", response_model=BrandMatchResult)
async def match_brand(
    request: BrandMatchRequest,
    embedder: VisualEmbedderProtocol = Depends(get_visual_embedder),
    matcher: BrandMatcher = Depends(get_brand_matcher),
) -> BrandMatchResult:
    query_embedding = await embedder.embed_image(request.image_b64)
    return matcher.match(query_embedding=query_embedding, current_domain=request.current_domain)


@app.post("/v1/explain", response_model=ExplainResult)
async def explain(
    request: ExplainRequest,
    provider: ExplanationProvider = Depends(get_explanation_provider),
) -> ExplainResult:
    # Receives only the precomputed verdict; the raw content never reaches this point (LGPD).
    try:
        return await provider.explain(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Explanation unavailable right now.") from exc
