from contracts import ThreatLevel, Persuasion

CATALOG: dict[tuple[ThreatLevel, Persuasion | None], tuple[str, str]] = {
    (ThreatLevel.SCAM, Persuasion.AFFECTIVE_COERCION): (
        "Esta mensagem tem fortes indícios do golpe do novo número ou falso parente.",
        "Não faça nenhum pagamento via PIX. Ligue imediatamente para o número habitual de telefone do seu familiar para confirmar.",
    ),
    (ThreatLevel.SCAM, Persuasion.FINANCIAL_THREAT): (
        "Esta mensagem parece ser uma falsa ameaça de bloqueio de conta bancária ou cobrança indevida.",
        "Não clique em links e não forneça senhas. Abra diretamente o aplicativo oficial do seu banco no celular.",
    ),
    (ThreatLevel.SCAM, Persuasion.URGENCY): (
        "Esta mensagem utiliza pressão de urgência para forçar uma transferência ou pagamento imediato.",
        "Desconfie de qualquer solicitação urgente. Não transfira valores sem antes consultar alguém de sua confiança.",
    ),
    (ThreatLevel.SCAM, None): (
        "Detectamos indícios de tentativa de golpe nesta mensagem.",
        "Não responda, não clique em links e não faça pagamentos ou transferências solicitadas.",
    ),
    (ThreatLevel.SAFE, None): (
        "Não encontramos sinais de golpe nesta mensagem.",
        "Mesmo assim, lembre-se: nunca envie senhas ou códigos recebidos por SMS para ninguém.",
    ),
    (ThreatLevel.CAUTION, None): (
        "Atenção: esta mensagem requer cautela antes de tomar qualquer atitude.",
        "O conteúdo contém propostas ou links suspeitos. Confirme as informações diretamente pelos canais oficiais.",
    ),
    (ThreatLevel.INCONCLUSIVE, None): (
        "Não foi possível concluir a verificação com total certeza no momento.",
        "Por precaução, não clique em links, não forneça dados e peça ajuda a alguém de confiança.",
    ),
}


def get_verdict_texts(
    threat: ThreatLevel,
    persuasion: Persuasion | None = None,
    category: str | None = None,
) -> tuple[str, str]:
    """
    Returns the (verdict_plain, action_advice) pair in clear, warm and direct language
    aimed at older adults, with a fallback per threat level.
    """
    if category == "brand_spoofing":
        return (
            "Atenção: esta página imita visualmente uma instituição oficial (golpe de falso site ou imitação de marca).",
            "Não digite senhas nem dados pessoais. Feche esta página imediatamente e acesse o site oficial da instituição diretamente pelo navegador.",
        )

    if persuasion and (threat, persuasion) in CATALOG:
        return CATALOG[(threat, persuasion)]

    if (threat, None) in CATALOG:
        return CATALOG[(threat, None)]

    return (
        "Verificação concluída.",
        "Sempre desconfie de mensagens que peçam dinheiro, senhas ou transferências.",
    )
