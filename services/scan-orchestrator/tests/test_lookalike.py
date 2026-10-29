import pytest

from scan_orchestrator.domain.lookalike import find_imitated_domain

PROTECTED = ["bb.com.br", "bancodobrasil.com.br", "itau.com.br", "nubank.com.br", "caixa.gov.br", "mercadolivre.com.br"]


@pytest.mark.parametrize(
    "domain",
    ["bb.com.br", "www.bb.com.br", "internetbanking.caixa.gov.br", "nubank.com.br", "google.com", "padariadobairro.com.br"],
)
def test_official_and_unrelated_domains_are_not_lookalikes(domain):
    assert find_imitated_domain(domain, PROTECTED) is None


@pytest.mark.parametrize(
    "domain,imitated",
    [
        ("bancodobrails.com", "bancodobrasil.com.br"),  # transposed letters
        ("nubamk.com.br", "nubank.com.br"),  # one letter swapped
        ("mercadolivre.com", "mercadolivre.com.br"),  # same name, other suffix
        ("itau-seguranca.com", "itau.com.br"),  # brand plus extra words (combosquatting)
        ("seguro.itau-app.net", "itau.com.br"),
        ("1tau.com.br", "itau.com.br"),  # digit that looks like a letter
        ("nubanк.com.br", "nubank.com.br"),  # Cyrillic "к"
        ("xn--nuban-yxe.com.br", "nubank.com.br"),  # the same domain in punycode
    ],
)
def test_lookalikes_point_to_the_imitated_official_domain(domain, imitated):
    assert find_imitated_domain(domain, PROTECTED) == imitated


def test_short_brand_names_only_match_exactly_to_avoid_false_alarms():
    # "bb" is two letters: any edit distance or substring match would flag half the internet.
    assert find_imitated_domain("bbc.com", PROTECTED) is None
    assert find_imitated_domain("bb.net", PROTECTED) == "bb.com.br"
