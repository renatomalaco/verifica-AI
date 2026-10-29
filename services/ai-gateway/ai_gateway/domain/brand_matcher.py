import math
from dataclasses import dataclass, field
from typing import Protocol
from contracts import BrandMatchResult
from contracts.protected_brands import PROTECTED_BRANDS


@dataclass(frozen=True)
class ProtectedBrand:
    name: str
    official_domains: list[str]
    embedding: list[float] = field(default_factory=list)


class BrandCatalogProtocol(Protocol):
    def get_all_brands(self) -> list[ProtectedBrand]:
        ...


class FakeBrandCatalog:
    def __init__(self, brands: list[ProtectedBrand]) -> None:
        self._brands = list(brands)

    def get_all_brands(self) -> list[ProtectedBrand]:
        return list(self._brands)


def one_hot(index: int, dimension: int) -> list[float]:
    return [1.0 if i == index else 0.0 for i in range(dimension)]


class DefaultBrandCatalog(BrandCatalogProtocol):
    def __init__(self, dimension: int = 768) -> None:
        self._brands = [
            # Placeholder embeddings until the pgvector seed with real logos exists (R4).
            ProtectedBrand(name=name, official_domains=list(domains), embedding=one_hot(i, dimension))
            for i, (name, domains) in enumerate(PROTECTED_BRANDS.items())
        ]

    def get_all_brands(self) -> list[ProtectedBrand]:
        return list(self._brands)


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0

    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return dot / (norm_a * norm_b)


def _check_dimension(query: list[float], brands: list[ProtectedBrand]) -> None:
    expected = {len(b.embedding) for b in brands}
    if expected and expected != {len(query)}:
        raise ValueError(f"Embedding dimension {len(query)} does not match the catalog dimension {sorted(expected)}")


class BrandMatcher:
    """Compares a page/logo visual embedding against protected brands to detect spoofing."""

    def __init__(self, catalog: BrandCatalogProtocol, threshold: float = 0.85) -> None:
        self._catalog = catalog
        self._threshold = threshold

    def match(self, query_embedding: list[float], current_domain: str | None = None) -> BrandMatchResult:
        brands = self._catalog.get_all_brands()
        _check_dimension(query_embedding, brands)
        best_brand: ProtectedBrand | None = None
        best_similarity = 0.0

        for brand in brands:
            sim = cosine_similarity(query_embedding, brand.embedding)
            if sim > best_similarity:
                best_similarity = sim
                best_brand = brand

        if best_brand is None or best_similarity < self._threshold:
            return BrandMatchResult(
                matched_brand=None,
                is_spoofing=False,
                similarity=round(best_similarity, 4),
                official_domains=[],
            )

        # A protected brand matched with high similarity:
        is_official = False
        if current_domain:
            clean_domain = current_domain.lower().strip()
            for official in best_brand.official_domains:
                if clean_domain == official or clean_domain.endswith("." + official):
                    is_official = True
                    break

        is_spoofing = not is_official

        return BrandMatchResult(
            matched_brand=best_brand.name,
            is_spoofing=is_spoofing,
            similarity=round(best_similarity, 4),
            official_domains=best_brand.official_domains,
        )
