"""Brands whose official domains the system protects: shared by Visual RAG and typosquatting."""

PROTECTED_BRANDS: dict[str, tuple[str, ...]] = {
    "Banco do Brasil": ("bb.com.br", "bancodobrasil.com.br"),
    "Nubank": ("nubank.com.br",),
    "Caixa Econômica Federal": ("caixa.gov.br",),
    "Itaú Unibanco": ("itau.com.br",),
    "Bradesco": ("bradesco.com.br",),
    "Santander": ("santander.com.br",),
    "Mercado Livre": ("mercadolivre.com.br",),
    "Correios": ("correios.com.br",),
    "Receita Federal / Gov.br": ("gov.br", "receita.fazenda.gov.br"),
}


def protected_domains() -> list[str]:
    return [domain for domains in PROTECTED_BRANDS.values() for domain in domains]
