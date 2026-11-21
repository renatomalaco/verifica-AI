"""Addresses the product can call official: each one proven on the public .br registry.

Rules for adding one:
- only .com.br and .gov.br, where rdap.registro.br shows the registered owner and CNPJ;
- never a platform that hosts other people's pages (site builders, forms, link shorteners),
  because a scam can live on those under the platform's own domain;
- recheck with `curl https://rdap.registro.br/domain/<domain>` and update `checked_on`.
"""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class OfficialAddress:
    domain: str
    registrant: str
    registrant_cnpj: str
    checked_on: date


_CHECKED = date(2026, 11, 21)

OFFICIAL_ADDRESSES: tuple[OfficialAddress, ...] = (
    OfficialAddress("bb.com.br", "BANCO DO BRASIL S.A.", "00.000.000/0001-91", _CHECKED),
    OfficialAddress("bancodobrasil.com.br", "BANCO DO BRASIL S.A.", "00.000.000/0001-91", _CHECKED),
    OfficialAddress("caixa.gov.br", "CAIXA ECONOMICA FEDERAL", "00.360.305/0001-04", _CHECKED),
    OfficialAddress("nubank.com.br", "NU PAGAMENTOS SA", "18.236.120/0001-58", _CHECKED),
    OfficialAddress("itau.com.br", "Itau Unibanco S.A.", "60.701.190/0001-04", _CHECKED),
    OfficialAddress("bradesco.com.br", "BANCO BRADESCO SA", "60.746.948/0001-12", _CHECKED),
    OfficialAddress(
        "santander.com.br", "Banco Santander (Brasil) S.A.", "90.400.888/0001-42", _CHECKED
    ),
    OfficialAddress(
        "correios.com.br",
        "Empresa Brasileira de Correios e Telégrafos",
        "34.028.316/0001-03",
        _CHECKED,
    ),
    OfficialAddress(
        "mercadolivre.com.br", "Mercado Livre Brasil Ltda.", "03.007.331/0001-41", _CHECKED
    ),
    OfficialAddress(
        "amazon.com.br",
        "Amazon Servicos de Varejo do Brasil Ltda.",
        "15.436.940/0001-03",
        _CHECKED,
    ),
)


def official_registrant(host: str) -> str | None:
    """Registered owner when the host is an official domain or one of its subdomains."""
    for address in OFFICIAL_ADDRESSES:
        if host == address.domain or host.endswith("." + address.domain):
            return address.registrant
    return None
