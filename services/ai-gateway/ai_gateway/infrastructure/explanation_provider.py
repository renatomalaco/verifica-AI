import json

import httpx
from pydantic import ValidationError

from contracts import ExplainRequest, ExplainResult, ThreatLevel
from ai_gateway.domain.explanation import EXPLAIN_SYSTEM_PROMPT, build_explain_prompt

_OPENING = {
    ThreatLevel.SCAM: "Isto tem cara de golpe. Veja por quê.",
    ThreatLevel.CAUTION: "Aqui vale ter cuidado antes de fazer qualquer coisa.",
    ThreatLevel.SAFE: "O Verifica não encontrou sinais de golpe aqui.",
    ThreatLevel.INCONCLUSIVE: "Desta vez não deu para ter certeza.",
}

_BY_CATEGORY = {
    "blacklist_feed": "Este endereço já está em listas de golpes conhecidos.",
    "embedded_phishing_link": "O link que veio junto leva para um site de golpe conhecido.",
    "urgencia": "A mensagem tenta te apressar. Golpistas fazem isso para você não parar e pensar.",
    "ameaca_financeira": "A mensagem ameaça bloquear sua conta ou cobrar algo. Bancos não avisam assim.",
    "coercao_afetiva": "A mensagem finge ser alguém da família pedindo dinheiro com pressa.",
    "antibot_challenge": "O site não deixou o Verifica olhar por dentro, e isso já é motivo de desconfiança.",
}


class FakeExplanationProvider:
    """Deterministic rule-based explanation, for tests and local use without an LLM."""

    async def explain(self, request: ExplainRequest) -> ExplainResult:
        lines = [_OPENING[request.threat_level]]

        brand = request.domain_signals.get("spoofed_brand")
        if request.category == "brand_spoofing" and brand:
            lines.append(f"A página copia o visual do {brand}, mas não está no endereço oficial.")
            official = request.domain_signals.get("official_domains")
            if official:
                lines.append(f"O endereço verdadeiro seria: {official}.")
        elif request.category in _BY_CATEGORY:
            lines.append(_BY_CATEGORY[request.category])

        if request.links_not_inspected:
            lines.append("Nem todos os links puderam ser abertos com segurança, então fique com o pé atrás.")

        lines.append(request.action_advice)
        return ExplainResult(lines=lines)


_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {"lines": {"type": "ARRAY", "items": {"type": "STRING"}}},
    "required": ["lines"],
}


class GeminiExplanationProvider:
    """Gemini client (generateContent) with JSON Schema structured output."""

    def __init__(self, base_url: str, api_key: str, model: str, timeout_seconds: float = 8.0):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def explain(self, request: ExplainRequest) -> ExplainResult:
        payload = {
            "systemInstruction": {"parts": [{"text": EXPLAIN_SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": build_explain_prompt(request)}]}],
            "generationConfig": {
                "temperature": 0.3,
                "responseMimeType": "application/json",
                "responseSchema": _RESPONSE_SCHEMA,
            },
        }
        # The key goes in the header, never the URL, so it does not leak into access logs.
        headers = {"x-goog-api-key": self._api_key, "Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    f"{self._base_url}/v1beta/models/{self._model}:generateContent",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise RuntimeError(f"Timeout na consulta ao Gemini ({self._timeout_seconds}s)") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Erro HTTP na consulta ao Gemini: {exc}") from exc

        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return ExplainResult.model_validate(json.loads(text))
        except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValidationError) as exc:
            raise RuntimeError("Resposta do Gemini fora do formato esperado") from exc
