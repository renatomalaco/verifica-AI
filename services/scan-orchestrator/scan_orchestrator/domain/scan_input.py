from dataclasses import dataclass
import hashlib
import re
import unicodedata

import tldextract

URL_ONLY_PATTERN = re.compile(r"^\s*(?:https?://|www\.)\S+\s*$", re.IGNORECASE)
EXPLICIT_LINK_PATTERN = re.compile(r"(?:https?://|www\.)[^\s/$.?#][^\s]*", re.IGNORECASE)
# Not preceded by "@" (emails) nor glued to another word; the suffix is checked by tldextract.
BARE_DOMAIN_CANDIDATE = re.compile(r"(?<![@\w.-])(?:[a-z0-9-]+\.)+[a-z0-9-]{2,}(?![\w@-])", re.IGNORECASE)
ZERO_WIDTH_PATTERN = re.compile(r"[\u200B-\u200D\uFEFF\u2060\u180E]")
TRAILING_PUNCTUATION = ".,;!?:)"

# Bundled public suffix list only: no network call at runtime.
_DOMAIN_PARSER = tldextract.TLDExtract(suffix_list_urls=())


def _clean(text: str) -> str:
    """Zero-width characters split a link in two for the eye-less regex (itau + U+200B + .com)."""
    return ZERO_WIDTH_PATTERN.sub("", unicodedata.normalize("NFKC", text))


def _is_registrable_domain(candidate: str) -> bool:
    parts = _DOMAIN_PARSER(candidate)
    return bool(parts.domain and parts.suffix)


def _find_links(text: str) -> list[str]:
    explicit = EXPLICIT_LINK_PATTERN.findall(text)
    remainder = EXPLICIT_LINK_PATTERN.sub(" ", text)
    bare = [c for c in BARE_DOMAIN_CANDIDATE.findall(remainder) if _is_registrable_domain(c)]
    links: list[str] = []
    for raw in explicit + bare:
        link = raw.strip().rstrip(TRAILING_PUNCTUATION)
        if link and link not in links:
            links.append(link)
    return links


@dataclass(frozen=True)
class ScanInput:
    """
    Immutable Value Object that wraps the raw input sent by the user,
    enforcing invariants and detecting content characteristics.
    """

    content: str = ""
    image_b64: str | None = None

    def __post_init__(self):
        has_content = bool(self.content and self.content.strip())
        has_image = bool(self.image_b64 and self.image_b64.strip())
        if not has_content and not has_image:
            raise ValueError("Invariant violated: content to inspect must not be empty.")

    @property
    def is_image(self) -> bool:
        return bool(self.image_b64 and self.image_b64.strip() and not (self.content and self.content.strip()))

    @property
    def is_url_only(self) -> bool:
        if self.image_b64:
            return False
        return bool(URL_ONLY_PATTERN.match(_clean(self.content).strip()))

    @property
    def has_links(self) -> bool:
        return bool(self.content) and bool(_find_links(_clean(self.content)))

    @property
    def sha256(self) -> str:
        data = (self.image_b64 or self.content).strip().encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    def extract_urls(self) -> list[str]:
        """Extracts all unique URLs from the content."""
        cleaned = _clean(self.content)
        if self.is_url_only:
            return [cleaned.strip()]
        return _find_links(cleaned)
