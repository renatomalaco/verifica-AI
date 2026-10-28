import re

# 1. JWT tokens
JWT_PATTERN = re.compile(r"eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]+")

# 2. PIX UUID (must run before long tokens so it is not mistaken for one)
PIX_UUID_PATTERN = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")

# 3. Long hex/alphanumeric tokens (>= 32 chars)
LONG_TOKEN_PATTERN = re.compile(r"\b[a-zA-Z0-9]{32,}\b")

# 4. Explicit passwords
PASSWORD_PATTERN = re.compile(r"(?i)\b(senha|password|pin|chave)\s*[:=]\s*(\S+)")

# 5. Cards (13 to 19 digit candidates separated by space, hyphen or nothing)
CARD_CANDIDATE_PATTERN = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")

# 6. CNPJ, formatted or as 14 digits
CNPJ_PATTERN = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")

# 7. CPF, formatted or as 11 standalone digits
CPF_FORMATTED_PATTERN = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
CPF_RAW_PATTERN = re.compile(r"\b\d{11}\b")

# 8. BR phone numbers (optional +55, 2-digit area code, 8 or 9 digits)
PHONE_PATTERN = re.compile(r"(?<![\w@.])(?:\+55\s?)?(?:\(?\d{2}\)?[\s-]?)?(?:9?\d{4})[\s-]?\d{4}\b")

# 9. Emails
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")


def _is_luhn_valid(card_number_str: str) -> bool:
    """Validates a credit card number with the Luhn algorithm."""
    digits = [int(c) for c in card_number_str if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for idx, d in enumerate(reverse_digits):
        if idx % 2 == 1:
            doubled = d * 2
            checksum += doubled - 9 if doubled > 9 else doubled
        else:
            checksum += d
    return checksum % 10 == 0


def mask_pii(text: str) -> str:
    """
    Replaces sensitive personal identifiers (PII) with structured tokens
    to ensure strict LGPD compliance before any AI inference.
    """
    if not text:
        return ""

    result = text

    # 1. JWT
    result = JWT_PATTERN.sub("[CHAVE_SENSIVEL]", result)

    # Emails go before every digit pattern, which would otherwise corrupt the address.
    result = EMAIL_PATTERN.sub("[EMAIL_MASCARADO]", result)

    # 2. PIX UUID
    result = PIX_UUID_PATTERN.sub("[PIX_MASCARADO]", result)

    # 3. Long tokens
    result = LONG_TOKEN_PATTERN.sub("[CHAVE_SENSIVEL]", result)

    # 4. Passwords
    result = PASSWORD_PATTERN.sub(r"\1: [CHAVE_SENSIVEL]", result)

    # 5. Bank cards validated by Luhn
    def _card_replacer(match: re.Match) -> str:
        raw = match.group(0)
        digits_only = re.sub(r"\D", "", raw)
        if _is_luhn_valid(digits_only):
            return "[CARTAO_MASCARADO]"
        return raw

    result = CARD_CANDIDATE_PATTERN.sub(_card_replacer, result)

    # 6. CNPJ
    result = CNPJ_PATTERN.sub("[CNPJ_MASCARADO]", result)

    # 7. CPF (formatted first, then raw 11 digits)
    result = CPF_FORMATTED_PATTERN.sub("[CPF_MASCARADO]", result)
    result = CPF_RAW_PATTERN.sub("[CPF_MASCARADO]", result)

    # 8. Brazilian phone numbers (only with at least 8 consecutive digits)
    def _phone_replacer(match: re.Match) -> str:
        val = match.group(0)
        digits = re.sub(r"\D", "", val)
        if len(digits) in (10, 11, 12, 13):
            return "[TELEFONE_MASCARADO]"
        return val

    result = PHONE_PATTERN.sub(_phone_replacer, result)

    return result
