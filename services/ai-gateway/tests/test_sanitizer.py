from ai_gateway.domain.sanitizer import sanitize_text


def test_sanitize_removes_zero_width_spaces():
    dirty = "Oi\u200b mãe,\u200c preciso de\ufeff ajuda"
    cleaned = sanitize_text(dirty)
    assert cleaned == "Oi mãe, preciso de ajuda"
    assert "\u200b" not in cleaned
    assert "\u200c" not in cleaned
    assert "\ufeff" not in cleaned


def test_sanitize_unicode_nfkc_normalization():
    dirty = "ＰＩＸ urgente"
    cleaned = sanitize_text(dirty)
    assert cleaned == "PIX urgente"


def test_sanitize_preserves_normal_text():
    normal = "Bom dia, tudo bem? Reunião às 14:00."
    assert sanitize_text(normal) == normal
