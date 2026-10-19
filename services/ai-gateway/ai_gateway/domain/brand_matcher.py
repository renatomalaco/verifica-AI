import math
from dataclasses import dataclass, field
from typing import Protocol
from contracts import BrandMatchResult


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


_DEFAULT_BRANDS = [
    ProtectedBrand(
        name="Banco do Brasil",
        official_domains=["bb.com.br", "bancodobrasil.com.br"],
        embedding=[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    ),
    ProtectedBrand(
        name="Nubank",
        official_domains=["nubank.com.br"],
        embedding=[0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    ),
    ProtectedBrand(
        name="Caixa Econômica Federal",
        official_domains=["caixa.gov.br"],
        embedding=[0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    ),
    ProtectedBrand(
        name="Itaú Unibanco",
        official_domains=["itau.com.br"],
        embedding=[0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
    ),
    ProtectedBrand(
        name="Mercado Livre",
        official_domains=["mercadolivre.com.br"],
        embedding=[0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
    ),
    ProtectedBrand(
        name="Receita Federal / Gov.br",
        official_domains=["gov.br", "receita.fazenda.gov.br"],
        embedding=[0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
    ),
]


class DefaultBrandCatalog(BrandCatalogProtocol):
    def __init__(self, brands: list[ProtectedBrand] | None = None) -> None:
        self._brands = brands or list(_DEFAULT_BRANDS)

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


class BrandMatcher:
    """Compares a page/logo visual embedding against protected brands to detect spoofing."""

    def __init__(self, catalog: BrandCatalogProtocol, threshold: float = 0.85) -> None:
        self._catalog = catalog
        self._threshold = threshold

    def match(self, query_embedding: list[float], current_domain: str | None = None) -> BrandMatchResult:
        brands = self._catalog.get_all_brands()
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
