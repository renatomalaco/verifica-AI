import pytest
from contracts import BrandMatchRequest, BrandMatchResult
from ai_gateway.domain.brand_matcher import (
    ProtectedBrand,
    BrandMatcher,
    cosine_similarity,
    FakeBrandCatalog,
)
from ai_gateway.domain.visual_embedder import FakeVisualEmbedder


def test_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert cosine_similarity(v1, v2) == pytest.approx(1.0)

    v3 = [0.0, 1.0, 0.0]
    assert cosine_similarity(v1, v3) == pytest.approx(0.0)


@pytest.fixture
def brand_catalog():
    bb_vec = [1.0, 0.0, 0.0]
    nubank_vec = [0.0, 1.0, 0.0]
    brands = [
        ProtectedBrand(
            name="Banco do Brasil",
            official_domains=["bb.com.br", "bancodobrasil.com.br"],
            embedding=bb_vec,
        ),
        ProtectedBrand(
            name="Nubank",
            official_domains=["nubank.com.br"],
            embedding=nubank_vec,
        ),
    ]
    return FakeBrandCatalog(brands)


def test_brand_matcher_detects_spoofing_when_domain_is_unofficial(brand_catalog):
    # Simulates an image vector highly similar to Banco do Brasil
    matcher = BrandMatcher(catalog=brand_catalog, threshold=0.85)
    query_vec = [0.98, 0.05, 0.0]

    result = matcher.match(
        query_embedding=query_vec,
        current_domain="bb-seguro-atualizacao.xyz",
    )

    assert result.matched_brand == "Banco do Brasil"
    assert result.similarity >= 0.85
    assert result.is_spoofing is True
    assert "bb.com.br" in result.official_domains


def test_brand_matcher_allows_legitimate_domain(brand_catalog):
    matcher = BrandMatcher(catalog=brand_catalog, threshold=0.85)
    query_vec = [0.98, 0.05, 0.0]

    result = matcher.match(
        query_embedding=query_vec,
        current_domain="bancodobrasil.com.br",
    )

    assert result.matched_brand == "Banco do Brasil"
    assert result.similarity >= 0.85
    assert result.is_spoofing is False


def test_brand_matcher_below_threshold_returns_no_brand(brand_catalog):
    matcher = BrandMatcher(catalog=brand_catalog, threshold=0.85)
    query_vec = [0.0, 0.0, 1.0]  # Orthogonal to every known brand

    result = matcher.match(
        query_embedding=query_vec,
        current_domain="qualquer-site.com",
    )

    assert result.matched_brand is None
    assert result.is_spoofing is False
    assert result.similarity < 0.85
