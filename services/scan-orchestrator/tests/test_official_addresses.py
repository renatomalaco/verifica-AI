import re

import pytest

from scan_orchestrator.domain.official_addresses import OFFICIAL_ADDRESSES, official_registrant


@pytest.mark.parametrize(
    "host, registrant",
    [
        ("mercadolivre.com.br", "Mercado Livre Brasil Ltda."),
        ("www.mercadolivre.com.br", "Mercado Livre Brasil Ltda."),
        ("www.amazon.com.br", "Amazon Servicos de Varejo do Brasil Ltda."),
    ],
)
def test_an_official_domain_and_its_subdomains_name_the_registered_owner(host, registrant):
    assert official_registrant(host) == registrant


@pytest.mark.parametrize(
    "host",
    [
        "mercadolivre.com.br.golpe.com",
        "falsomercadolivre.com.br",
        "mercadolivre-ofertas.com",
        "amazon.com",  # .com hides the owner: not checked, so not claimed
        "",
    ],
)
def test_lookalikes_and_unchecked_domains_are_not_official(host):
    assert official_registrant(host) is None


@pytest.mark.parametrize("address", OFFICIAL_ADDRESSES, ids=lambda a: a.domain)
def test_every_official_address_keeps_its_registry_proof(address):
    # The registry only shows the owner for these suffixes; anything else cannot be proven.
    assert address.domain.endswith((".com.br", ".gov.br"))
    assert address.registrant
    assert re.fullmatch(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", address.registrant_cnpj)
    assert address.checked_on.year >= 2026
