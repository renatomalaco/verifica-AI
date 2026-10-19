from typing import Protocol

from contracts import ExplainRequest, ExplainResult
from ai_gateway.domain.data_masker import mask_pii
from ai_gateway.domain.envelope import SYSTEM_DIRECTIVE, build_envelope
from ai_gateway.domain.sanitizer import sanitize_text

EXPLAIN_SYSTEM_PROMPT = (
    "Você explica, para uma pessoa idosa, por que uma mensagem, link ou print recebeu um veredito "
    "de verificação de golpe. Use português do Brasil, frases curtas, sem termos técnicos e sem siglas. "
    "Escreva de 3 a 5 linhas, cada uma com uma ideia só. Nunca fale em primeira pessoa (sem \"eu\"): "
    "quando precisar de sujeito, use \"o Verifica\" ou frases impessoais. Não invente fatos que não estejam nos dados, "
    "não peça dados pessoais e não mude o veredito. "
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
        f"Veredito: {request.threat_level.value}",
        f"Canal: {request.channel.value}",
        f"Etapa que decidiu: {request.deciding_stage}",
        f"Categoria: {request.category or 'nenhuma'}",
        f"Resumo mostrado: {request.verdict_plain}",
        f"O que fazer mostrado: {request.action_advice}",
        f"Links não puderam ser abertos: {'sim' if request.links_not_inspected else 'não'}",
    ]
    lines += [f"Pontuação {k}: {v:.2f}" for k, v in sorted(request.scores.items())]
    lines += [f"Sinal {k}: {v}" for k, v in sorted(request.domain_signals.items())]
    masked = mask_pii(sanitize_text("\n".join(lines)))
    return build_envelope(masked)
