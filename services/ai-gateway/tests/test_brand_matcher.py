import pytest

from ai_gateway.domain.brand_matcher import (
    MatchPolicy,
    MatchZone,
    ensure_dimension,
    is_official_domain,
    official_domains_of,
)


@pytest.fixture
def policy() -> MatchPolicy:
    return MatchPolicy(threshold=0.82, gray_floor=0.70)


@pytest.mark.parametrize(
    ("similarity", "zone"),
    [(0.95, MatchZone.CONFIRMED), (0.82, MatchZone.CONFIRMED), (0.81, MatchZone.GRAY), (0.70, MatchZone.GRAY), (0.69, MatchZone.NONE)],
)
def test_similarity_falls_into_its_zone(policy, similarity, zone):
    assert policy.zone(similarity) is zone


def test_a_gray_floor_above_the_threshold_is_rejected():
    with pytest.raises(ValueError, match="gray_floor"):
        MatchPolicy(threshold=0.82, gray_floor=0.90)


@pytest.mark.parametrize(
    "host",
    ["bb.com.br", "www2.bancodobrasil.com.br", "BB.COM.BR.", "internetbanking.caixa.gov.br", "www.gov.br"],
)
def test_official_hosts_and_their_subdomains_are_recognized(host):
    official = ["bb.com.br", "bancodobrasil.com.br", "caixa.gov.br", "gov.br"]
    assert is_official_domain(host, official) is True


@pytest.mark.parametrize(
    "host",
    [
        "bb.com.br.atualizacao.xyz",  # the brand as a subdomain of another site
        "bb-seguro.com.br",
        "evilbb.com.br",
        "gov.br.golpe.com",
        "200.10.10.10",
        "",
    ],
)
def test_lookalike_hosts_are_not_official(host):
    assert is_official_domain(host, ["bb.com.br", "gov.br"]) is False


def test_official_domains_come_from_the_shared_brand_contract():
    assert official_domains_of("Nubank") == ["nubank.com.br"]
    assert official_domains_of("Marca desconhecida") == []


def test_an_embedding_of_another_dimension_fails_loudly():
    # A silent 0.0 similarity hid this mismatch before (B3).
    with pytest.raises(ValueError, match="dimension"):
        ensure_dimension([1.0, 0.0], expected=768)
    ensure_dimension([0.0] * 768, expected=768)
