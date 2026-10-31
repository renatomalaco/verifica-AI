from dataclasses import dataclass
from enum import Enum

import tldextract

from contracts.protected_brands import PROTECTED_BRANDS

_PARSER = tldextract.TLDExtract(suffix_list_urls=())  # bundled public suffix list, no network


@dataclass(frozen=True)
class BrandCandidate:
    """The protected brand whose reference image is closest to the query."""

    name: str
    similarity: float


class MatchZone(Enum):
    NONE = "none"
    GRAY = "gray"  # resembles a brand, but only a VLM may confirm it
    CONFIRMED = "confirmed"


@dataclass(frozen=True)
class MatchPolicy:
    threshold: float
    gray_floor: float

    def __post_init__(self) -> None:
        if self.gray_floor > self.threshold:
            raise ValueError(f"gray_floor {self.gray_floor} is above the threshold {self.threshold}")

    def zone(self, similarity: float) -> MatchZone:
        if similarity >= self.threshold:
            return MatchZone.CONFIRMED
        if similarity >= self.gray_floor:
            return MatchZone.GRAY
        return MatchZone.NONE


def official_domains_of(brand: str) -> list[str]:
    return list(PROTECTED_BRANDS.get(brand, ()))


def is_official_domain(host: str, official_domains: list[str]) -> bool:
    """Compares registrable domains (eTLD+1), so 'bb.com.br.atualizacao.xyz' is not 'bb.com.br'."""
    site = _PARSER(host.strip().lower().rstrip("."))
    return any(_belongs_to(site, entry) for entry in official_domains)


def _belongs_to(site: tldextract.ExtractResult, entry: str) -> bool:
    official = _PARSER(entry)
    if not official.domain:
        # The entry is a public suffix itself (gov.br): only the government registers under it.
        return bool(site.domain) and site.suffix == official.suffix
    return bool(site.domain) and (site.domain, site.suffix) == (official.domain, official.suffix)


def ensure_dimension(embedding: list[float], expected: int) -> None:
    if len(embedding) != expected:
        raise ValueError(f"Embedding dimension {len(embedding)} does not match the catalog dimension {expected}")
