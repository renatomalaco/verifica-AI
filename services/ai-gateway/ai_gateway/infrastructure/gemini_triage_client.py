import json
from dataclasses import dataclass

from contracts import Persuasion, TriageResult
from pydantic import ValidationError

from ai_gateway.domain.envelope import SYSTEM_DIRECTIVE
from ai_gateway.infrastructure.gemini_http import generate_content

_SYSTEM_PROMPT = (
    "You triage messages, links and screenshot text for scams aimed at older adults in Brazil. "
    f"{SYSTEM_DIRECTIVE} "
    "Give the probability (0 to 1) that the content attempts a scam, banking fraud "
    "or social engineering, "
    "the probability (0 to 1) that a conclusive decision depends on visual appearance, "
    "logo or layout, "
    "and the main persuasion technique."
)

_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "is_phishing": {"type": "NUMBER"},
        "requires_visual_inspection": {"type": "NUMBER"},
        "persuasion": {"type": "STRING", "enum": [p.value for p in Persuasion]},
    },
    "required": ["is_phishing", "requires_visual_inspection", "persuasion"],
}


@dataclass(frozen=True)
class MeasuredTriage:
    result: TriageResult
    input_tokens: int
    output_tokens: int  # answer plus thinking tokens: both are billed at the output price


class GeminiTriageClient:
    """Text triage on Gemini with structured output; same contract as the Jev client."""

    def __init__(self, base_url: str, api_key: str, model: str, timeout_seconds: float = 8.0):
        self._base_url = base_url
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def classify(self, envelope: str) -> TriageResult:
        return (await self.measure(envelope)).result

    async def measure(self, envelope: str) -> MeasuredTriage:
        payload = {
            "systemInstruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": envelope}]}],
            "generationConfig": {
                "temperature": 0.0,
                "responseMimeType": "application/json",
                "responseSchema": _RESPONSE_SCHEMA,
            },
        }
        data = await generate_content(
            self._base_url, self._api_key, self._model, self._timeout_seconds, payload
        )
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            usage = data["usageMetadata"]
            return MeasuredTriage(
                result=TriageResult.model_validate(json.loads(text)),
                input_tokens=int(usage["promptTokenCount"]),
                output_tokens=int(usage.get("candidatesTokenCount", 0))
                + int(usage.get("thoughtsTokenCount", 0)),
            )
        except (KeyError, IndexError, TypeError, ValueError, ValidationError) as exc:
            raise RuntimeError("Gemini answer is not in the expected format") from exc
