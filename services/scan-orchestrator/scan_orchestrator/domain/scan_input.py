from dataclasses import dataclass
import hashlib
import re

URL_ONLY_PATTERN = re.compile(r"^\s*(?:https?://|www\.)\S+\s*$", re.IGNORECASE)
EMBEDDED_LINK_PATTERN = re.compile(
    r"(?:https?://|www\.)[^\s/$.?#].[^\s]*|\b[\w-]+\.(?:com|br|net|org|app|io|xyz|online|shop)\b",
    re.IGNORECASE,
)


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
        return bool(URL_ONLY_PATTERN.match(self.content.strip()))

    @property
    def has_links(self) -> bool:
        if not self.content:
            return False
        return bool(EMBEDDED_LINK_PATTERN.search(self.content))

    @property
    def sha256(self) -> str:
        data = (self.image_b64 or self.content).strip().encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    def extract_urls(self) -> list[str]:
        """Extracts all unique URLs from the content."""
        if self.is_url_only:
            return [self.content.strip()]
        matches = EMBEDDED_LINK_PATTERN.findall(self.content)
        cleaned_urls: list[str] = []
        for m in matches:
            url_clean = m.strip().rstrip(".,;!?:)")
            if url_clean and url_clean not in cleaned_urls:
                cleaned_urls.append(url_clean)
        return cleaned_urls
