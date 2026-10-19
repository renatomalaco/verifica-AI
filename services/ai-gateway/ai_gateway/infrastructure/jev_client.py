from typing import Protocol
import httpx
from contracts import TriageResult, Persuasion


class JevClient(Protocol):
    async def classify(self, envelope: str) -> TriageResult:
        ...


class FakeJevClient:
    """
    Deterministic simulator of the Jev model (TypeSafe AI) for local use and tests,
    based on the problem's triage rules and tolerant of accent variations.
    """

    async def classify(self, envelope: str) -> TriageResult:
        lowered = envelope.lower()

        has_new_number = any(w in lowered for w in ["troquei de número", "troquei de numero", "novo número", "novo numero"])
        has_relative = any(w in lowered for w in ["mãe", "mae", "pai", "filho", "filha", "pix"])

        # Fake relative scam / emotional coercion
        if has_new_number and has_relative:
            return TriageResult(
                is_phishing=0.96,
                requires_visual_inspection=0.02,
                persuasion=Persuasion.AFFECTIVE_COERCION,
            )

        # Financial threat / account lockout
        if any(w in lowered for w in ["bloqueio", "bloqueada", "cancelado"]) and any(
            w in lowered for w in ["conta", "banco", "cartão", "cartao"]
        ):
            return TriageResult(
                is_phishing=0.92,
                requires_visual_inspection=0.08,
                persuasion=Persuasion.FINANCIAL_THREAT,
            )

        # Plain urgency with payment
        if any(w in lowered for w in ["urgente", "imediato", "agora"]) and any(
            w in lowered for w in ["pix", "pague", "multa", "transferência", "transferencia"]
        ):
            return TriageResult(
                is_phishing=0.91,
                requires_visual_inspection=0.05,
                persuasion=Persuasion.URGENCY,
            )

        # Corporate content or safe small talk
        if any(w in lowered for w in ["reunião", "reuniao", "bom dia", "boa tarde", "sala", "anexo", "abraço", "abraco", "almoço", "almoco"]):
            return TriageResult(
                is_phishing=0.03,
                requires_visual_inspection=0.0,
                persuasion=Persuasion.NONE,
            )

        # Neutral/uncertain default (middle range)
        return TriageResult(
            is_phishing=0.45,
            requires_visual_inspection=0.10,
            persuasion=Persuasion.NONE,
        )


class HttpJevClient:
    """
    Real HTTP client for the Jev model (TypeSafe AI).
    System One endpoint with typed decisions (noul / choice).
    """

    def __init__(self, base_url: str, api_key: str, timeout_seconds: float = 1.5):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def classify(self, envelope: str) -> TriageResult:
        payload = {
            "model": "jev-latest",
            "state": envelope,
            "questions": {
                "is_phishing": {
                    "type": "noul",
                    "prompt": "Este conteúdo tenta aplicar golpe, fraude bancária ou engenharia social?",
                },
                "requires_visual_inspection": {
                    "type": "noul",
                    "prompt": "A decisão conclusiva de risco depende da aparência visual, logotipo ou layout?",
                },
                "persuasion": {
                    "type": "choice",
                    "options": ["urgencia", "ameaca_financeira", "coercao_afetiva", "nenhuma"],
                },
            },
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    f"{self._base_url}/v1/systemone",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise RuntimeError(f"Timeout na consulta ao modelo Jev ({self._timeout_seconds}s)") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Erro HTTP na consulta ao modelo Jev: {exc}") from exc

        answers = data.get("answers", {})
        is_phishing = float(answers.get("is_phishing", {}).get("probability", 0.5))
        requires_visual = float(answers.get("requires_visual_inspection", {}).get("probability", 0.0))
        persuasion_str = answers.get("persuasion", {}).get("selected", "nenhuma")

        try:
            persuasion = Persuasion(persuasion_str)
        except ValueError:
            persuasion = Persuasion.NONE

        return TriageResult(
            is_phishing=is_phishing,
            requires_visual_inspection=requires_visual,
            persuasion=persuasion,
        )
