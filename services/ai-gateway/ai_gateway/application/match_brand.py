import logging
from typing import Protocol

from contracts import BrandMatchRequest, BrandMatchResult, ImageSource
from ai_gateway.domain.brand_matcher import (
    BrandCandidate,
    MatchPolicy,
    MatchZone,
    ensure_dimension,
    is_official_domain,
    official_domains_of,
)

logger = logging.getLogger(__name__)


class VisualEmbedder(Protocol):
    async def embed_image(self, image_b64: str) -> list[float]:
        ...


class BrandCatalog(Protocol):
    async def nearest(self, embedding: list[float]) -> BrandCandidate | None:
        ...


class BrandVerifier(Protocol):
    async def shows_brand(self, image_b64: str, brand: str) -> bool:
        ...


class EmptyBrandCatalog(RuntimeError):
    """No reference images were seeded, so nothing can be compared."""


class MatchBrandUseCase:
    """Visual RAG: embedding -> nearest protected brand (pgvector) -> VLM only in the gray zone."""

    def __init__(
        self,
        embedder: VisualEmbedder,
        catalog: BrandCatalog,
        policy: MatchPolicy,
        dimension: int,
        verifier: BrandVerifier | None = None,
    ) -> None:
        self._embedder = embedder
        self._catalog = catalog
        self._policy = policy
        self._dimension = dimension
        self._verifier = verifier

    async def run(self, request: BrandMatchRequest) -> BrandMatchResult:
        embedding = await self._embedder.embed_image(request.image_b64)
        ensure_dimension(embedding, self._dimension)
        candidate = await self._catalog.nearest(embedding)
        if candidate is None:
            raise EmptyBrandCatalog("the protected brands catalog has no reference images")

        similarity = round(candidate.similarity, 4)
        zone = self._policy.zone(candidate.similarity)
        if zone is MatchZone.NONE:
            return BrandMatchResult(similarity=similarity)

        official = official_domains_of(candidate.name)
        if request.current_domain and is_official_domain(request.current_domain, official):
            matched = candidate.name if zone is MatchZone.CONFIRMED else None
            return BrandMatchResult(matched_brand=matched, similarity=similarity, official_domains=official)

        if zone is MatchZone.CONFIRMED or await self._vlm_confirms(request, candidate.name):
            return BrandMatchResult(
                matched_brand=candidate.name, is_spoofing=True, similarity=similarity, official_domains=official
            )
        return BrandMatchResult(possible_brand=candidate.name, similarity=similarity, official_domains=official)

    async def _vlm_confirms(self, request: BrandMatchRequest, brand: str) -> bool:
        if self._verifier is None or request.image_source is not ImageSource.PAGE_SCREENSHOT:
            return False
        try:
            return await self._verifier.shows_brand(request.image_b64, brand)
        except RuntimeError:
            logger.warning("VLM brand check failed; the gray zone stays a signal", exc_info=True)
            return False
