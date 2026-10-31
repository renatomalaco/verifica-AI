import pytest

from contracts import BrandMatchRequest, ImageSource
from ai_gateway.application.match_brand import EmptyBrandCatalog, MatchBrandUseCase
from ai_gateway.domain.brand_matcher import MatchPolicy
from ai_gateway.infrastructure.fakes import FakeBrandCatalog, FakeBrandVerifier, FakeVisualEmbedder

DIM = 3
BB_LOGO = [1.0, 0.0, 0.0]


def _use_case(query: list[float], verifier: FakeBrandVerifier | None = None) -> MatchBrandUseCase:
    catalog = FakeBrandCatalog({"Banco do Brasil": [BB_LOGO], "Nubank": [[0.0, 1.0, 0.0]]})
    return MatchBrandUseCase(
        embedder=FakeVisualEmbedder(default_embedding=query, dimension=DIM),
        catalog=catalog,
        policy=MatchPolicy(threshold=0.82, gray_floor=0.70),
        dimension=DIM,
        verifier=verifier,
    )


def _request(domain: str | None, source: ImageSource = ImageSource.PAGE_SCREENSHOT) -> BrandMatchRequest:
    return BrandMatchRequest(image_b64="aGVsbG8=", current_domain=domain, image_source=source)


ABOVE_THRESHOLD = [0.98, 0.05, 0.0]  # cosine ~0.999 with the BB logo
GRAY_ZONE = [0.75, 0.66, 0.0]  # cosine ~0.75 with the BB logo


async def test_brand_above_the_threshold_on_another_domain_is_spoofing_without_asking_the_vlm():
    verifier = FakeBrandVerifier(answer=False)

    result = await _use_case(ABOVE_THRESHOLD, verifier).run(_request("bb-recadastro.xyz"))

    assert result.is_spoofing is True
    assert result.matched_brand == "Banco do Brasil"
    assert "bb.com.br" in result.official_domains
    assert result.similarity >= 0.82
    assert verifier.calls == 0


async def test_brand_on_its_official_domain_is_not_spoofing():
    result = await _use_case(ABOVE_THRESHOLD).run(_request("www2.bancodobrasil.com.br"))

    assert result.matched_brand == "Banco do Brasil"
    assert result.is_spoofing is False


async def test_gray_zone_without_a_vlm_is_only_a_signal():
    result = await _use_case(GRAY_ZONE).run(_request("bb-recadastro.xyz"))

    assert result.is_spoofing is False
    assert result.matched_brand is None
    assert result.possible_brand == "Banco do Brasil"


async def test_gray_zone_confirmed_by_the_vlm_is_spoofing():
    verifier = FakeBrandVerifier(answer=True)

    result = await _use_case(GRAY_ZONE, verifier).run(_request("bb-recadastro.xyz"))

    assert result.is_spoofing is True
    assert result.matched_brand == "Banco do Brasil"
    assert verifier.calls == 1


async def test_gray_zone_denied_by_the_vlm_stays_a_signal():
    result = await _use_case(GRAY_ZONE, FakeBrandVerifier(answer=False)).run(_request("bb-recadastro.xyz"))

    assert result.is_spoofing is False
    assert result.possible_brand == "Banco do Brasil"


async def test_a_persons_screenshot_never_goes_to_the_vlm():
    verifier = FakeBrandVerifier(answer=True)

    result = await _use_case(GRAY_ZONE, verifier).run(_request("bb-recadastro.xyz", ImageSource.USER_IMAGE))

    assert verifier.calls == 0
    assert result.is_spoofing is False
    assert result.possible_brand == "Banco do Brasil"


async def test_a_failing_vlm_leaves_the_gray_zone_as_a_signal():
    verifier = FakeBrandVerifier(error=RuntimeError("Gemini HTTP error"))

    result = await _use_case(GRAY_ZONE, verifier).run(_request("bb-recadastro.xyz"))

    assert result.is_spoofing is False
    assert result.possible_brand == "Banco do Brasil"


async def test_gray_zone_on_the_official_domain_skips_the_vlm():
    verifier = FakeBrandVerifier(answer=True)

    result = await _use_case(GRAY_ZONE, verifier).run(_request("bb.com.br"))

    assert result.is_spoofing is False
    assert result.possible_brand is None
    assert verifier.calls == 0


async def test_below_the_gray_floor_no_brand_is_reported():
    result = await _use_case([0.0, 0.0, 1.0]).run(_request("qualquer-site.com"))

    assert result.matched_brand is None
    assert result.possible_brand is None
    assert result.is_spoofing is False


async def test_an_empty_catalog_is_an_error_not_a_clean_result():
    # Without references nothing was compared; answering "no brand" would hide it.
    use_case = MatchBrandUseCase(
        embedder=FakeVisualEmbedder(default_embedding=BB_LOGO, dimension=DIM),
        catalog=FakeBrandCatalog({}),
        policy=MatchPolicy(threshold=0.82, gray_floor=0.70),
        dimension=DIM,
    )
    with pytest.raises(EmptyBrandCatalog):
        await use_case.run(_request("bb-recadastro.xyz"))


async def test_an_embedder_of_another_dimension_fails_loudly():
    with pytest.raises(ValueError, match="dimension"):
        await _use_case([1.0, 0.0]).run(_request("x.com"))


async def test_fake_embedder_builds_a_unit_vector_of_the_requested_size():
    vector = await FakeVisualEmbedder(dimension=768).embed_image("aGVsbG8=")
    assert len(vector) == 768
    assert sum(v * v for v in vector) == pytest.approx(1.0, abs=1e-3)
