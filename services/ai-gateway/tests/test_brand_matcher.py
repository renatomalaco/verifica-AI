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


# --- Embedding dimension contract (B3) ---

async def test_runtime_embedder_and_default_catalog_share_the_configured_dimension():
    from ai_gateway.api.main import get_brand_matcher, get_visual_embedder
    from ai_gateway.settings import Settings

    dim = Settings().EMBEDDING_DIM
    vector = await get_visual_embedder(Settings()).embed_image("aGVsbG8=")
    brands = get_brand_matcher(Settings())._catalog.get_all_brands()

    assert dim == 768
    assert len(vector) == dim
    assert all(len(brand.embedding) == dim for brand in brands)


async def test_fake_embedder_builds_a_unit_vector_of_the_requested_size():
    vector = await FakeVisualEmbedder(dimension=768).embed_image("aGVsbG8=")
    assert len(vector) == 768
    assert sum(v * v for v in vector) == pytest.approx(1.0, abs=1e-3)


def test_matcher_rejects_an_embedding_with_another_dimension(brand_catalog):
    # A silent 0.0 similarity hid this mismatch before; it must fail loudly.
    matcher = BrandMatcher(catalog=brand_catalog, threshold=0.85)
    with pytest.raises(ValueError, match="dimension"):
        matcher.match(query_embedding=[1.0, 0.0], current_domain="x.com")
