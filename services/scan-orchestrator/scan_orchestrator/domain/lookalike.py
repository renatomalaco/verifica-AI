"""Typosquatting: does a domain imitate the official domain of a protected brand?"""

import re

import tldextract

_PARSER = tldextract.TLDExtract(suffix_list_urls=())  # bundled public suffix list, no network

# Characters people read as the same letter (digits, Cyrillic and Greek look-alikes).
_CONFUSABLES = str.maketrans({
    "0": "o", "1": "l", "i": "l", "|": "l", "3": "e", "4": "a", "5": "s", "7": "t", "8": "b",
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "к": "k",
    "і": "l", "ӏ": "l", "ԁ": "d", "ɡ": "g", "ո": "n", "ս": "u", "ο": "o", "α": "a", "ν": "v",
})
_MULTI_CHAR = (("rn", "m"), ("vv", "w"))

MIN_TOKEN_LEN = 4  # "bb" inside a hostname is noise; "itau" or "caixa" is not
MIN_FUZZY_LEN = 5  # edit distance on short names flags unrelated sites


def find_imitated_domain(domain: str, protected: list[str]) -> str | None:
    host = _decode_idn(domain.lower().strip("."))
    if any(_is_same_or_subdomain(host, official) for official in protected):
        return None
    return next((official for official in protected if _imitates(host, official)), None)


def _is_same_or_subdomain(host: str, official: str) -> bool:
    return host == official or host.endswith("." + official)


def _imitates(host: str, official: str) -> bool:
    parts = _PARSER(host)
    label = _skeleton(parts.domain)
    brand = _skeleton(_PARSER(official).domain)
    if label == brand:
        return True
    if len(brand) >= MIN_FUZZY_LEN and _distance(label, brand) <= _max_distance(brand):
        return True
    if len(brand) < MIN_TOKEN_LEN:
        return False
    tokens = re.split(r"[-.]", f"{parts.subdomain}.{parts.domain}")
    return brand in {_skeleton(t) for t in tokens if t}


def _max_distance(brand: str) -> int:
    return 1 if len(brand) < 10 else 2


def _decode_idn(host: str) -> str:
    labels = []
    for label in host.split("."):
        try:
            labels.append(label.encode("ascii").decode("idna") if label.startswith("xn--") else label)
        except UnicodeError:
            labels.append(label)
    return ".".join(labels)


def _skeleton(text: str) -> str:
    folded = text.lower()
    for chars, letter in _MULTI_CHAR:
        folded = folded.replace(chars, letter)
    return folded.translate(_CONFUSABLES)


def _distance(a: str, b: str) -> int:
    """Damerau-Levenshtein (optimal string alignment): swaps of adjacent letters cost 1."""
    rows = [list(range(len(b) + 1))] + [[i] + [0] * len(b) for i in range(1, len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            rows[i][j] = min(rows[i - 1][j] + 1, rows[i][j - 1] + 1, rows[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                rows[i][j] = min(rows[i][j], rows[i - 2][j - 2] + 1)
    return rows[len(a)][len(b)]
