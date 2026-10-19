import re

_CLOUDFLARE_PATTERNS = [
    re.compile(r"cf-challenge-running", re.IGNORECASE),
    re.compile(r"cf-turnstile", re.IGNORECASE),
    re.compile(r"cloudflare\s*ray\s*id", re.IGNORECASE),
    re.compile(r"attention\s*required!\s*\|\s*cloudflare", re.IGNORECASE),
]

_GENERIC_ANTIBOT_PATTERNS = [
    re.compile(r"datadome", re.IGNORECASE),
    re.compile(r"incapsula", re.IGNORECASE),
    re.compile(r"recaptcha", re.IGNORECASE),
    re.compile(r"bot\s*detection", re.IGNORECASE),
]


def check_antibot_block(html: str, title: str = "") -> tuple[bool, str | None]:
    """Detects whether a captured page is an antibot/WAF/challenge block screen."""
    combined_sample = f"{title} {html[:4000]}"

    if "just a moment..." in title.lower():
        return True, "cloudflare_challenge"

    for pattern in _CLOUDFLARE_PATTERNS:
        if pattern.search(combined_sample):
            return True, "cloudflare_challenge"

    for pattern in _GENERIC_ANTIBOT_PATTERNS:
        if pattern.search(combined_sample):
            return True, "antibot_challenge"

    return False, None
