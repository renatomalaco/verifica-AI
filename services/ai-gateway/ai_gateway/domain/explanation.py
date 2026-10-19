from typing import Protocol

from contracts import ExplainRequest, ExplainResult, Locale
from ai_gateway.domain.data_masker import mask_pii
from ai_gateway.domain.envelope import SYSTEM_DIRECTIVE, build_envelope
from ai_gateway.domain.sanitizer import sanitize_text

LANGUAGE_NAMES: dict[Locale, str] = {
    Locale.PT_BR: "Brazilian Portuguese",
}


def explain_system_prompt(locale: Locale) -> str:
    """The instructions are in English; the answer must come in the person's language."""
    return (
        "You explain to an older adult why a message, link or screenshot received a scam-check verdict. "
        f"Write in {LANGUAGE_NAMES[locale]}, with short sentences, no technical terms and no acronyms. "
        "Write 3 to 5 lines, one idea per line. Never speak in the first person (no \"I\"): "
        "when a subject is needed, use \"Verifica\" or impersonal sentences. Do not invent facts that are not "
        "in the data, do not ask for personal data and do not change the verdict. "
        + SYSTEM_DIRECTIVE
    )


class ExplanationProvider(Protocol):
    async def explain(self, request: ExplainRequest) -> ExplainResult:
        ...


def build_explain_prompt(request: ExplainRequest) -> str:
    """
    Builds the text sent to the LLM from the precomputed verdict. Every field
    is sanitized and masked and kept inside the anti-injection envelope,
    because domain signals come from third-party-controlled pages.
    """
    lines = [
        f"Verdict: {request.threat_level.value}",
        f"Channel: {request.channel.value}",
        f"Deciding stage: {request.deciding_stage}",
        f"Category: {request.category or 'none'}",
        f"Message shown to the person: {request.verdict_message.value}",
        f"Links that could not be opened: {'yes' if request.links_not_inspected else 'no'}",
    ]
    lines += [f"Score {k}: {v:.2f}" for k, v in sorted(request.scores.items())]
    lines += [f"Signal {k}: {v}" for k, v in sorted(request.domain_signals.items())]
    masked = mask_pii(sanitize_text("\n".join(lines)))
    return build_envelope(masked)
