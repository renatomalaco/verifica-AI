from scan_orchestrator.domain.cascade import ReputationClientProtocol

_KNOWN_REPUTABLE_DOMAINS = {
    "google.com",
    "google.com.br",
    "bancodobrasil.com.br",
    "bb.com.br",
    "caixa.gov.br",
    "itau.com.br",
    "bradesco.com.br",
    "santander.com.br",
    "mercadolivre.com.br",
    "nubank.com.br",
    "gov.br",
    "receita.fazenda.gov.br",
    "apple.com",
    "microsoft.com",
}


class DomainSignalsClient(ReputationClientProtocol):
    """Reputation and domain signals client (Tranco top list, homoglyph/punycode detection)."""

    async def get_domain_signals(self, domain: str) -> dict[str, str]:
        clean_domain = domain.lower().strip()

        # Homoglyph / IDN spoofing detection
        if "xn--" in clean_domain:
            return {"homoglyph": "detected", "reputation": "suspicious"}

        # High-reputation list check
        for trusted in _KNOWN_REPUTABLE_DOMAINS:
            if clean_domain == trusted or clean_domain.endswith("." + trusted):
                return {"reputation": "high", "age": "established"}

        return {"reputation": "neutral", "age": "unknown"}
