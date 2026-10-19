import unicodedata
import re

# Pattern for invisible and zero-width control characters
ZERO_WIDTH_PATTERN = re.compile(r"[\u200B-\u200D\uFEFF\u2060\u180E]")


def sanitize_text(text: str) -> str:
    """
    Normalizes the string to Unicode NFKC and strips invisible (zero-width) characters
    commonly used in adversarial attacks to bypass lexical and PII filters.
    """
    if not text:
        return ""
    # 1. Canonical compatibility normalization
    normalized = unicodedata.normalize("NFKC", text)
    # 2. Strip invisible characters
    cleaned = ZERO_WIDTH_PATTERN.sub("", normalized)
    return cleaned
