"""Stage 1 evidence from public sources: RDAP (registration), crt.sh (first certificate), Tranco (popularity)."""

import asyncio
from collections.abc import Callable
from datetime import date, datetime

import httpx
import redis.asyncio as aioredis
import tldextract

from scan_orchestrator.domain.domain_risk import DomainEvidence

_PARSER = tldextract.TLDExtract(suffix_list_urls=())
TRANCO_KEY = "tranco:rank"
Today = Callable[[], date]


def registrable(domain: str) -> str:
    return _PARSER(domain).top_domain_under_public_suffix or domain


def _days_since(moment: str, today: date) -> int:
    return (today - datetime.fromisoformat(moment.replace("Z", "+00:00")).date()).days


class RdapClient:
    def __init__(self, timeout_seconds: float = 3.0, today: Today = date.today) -> None:
        self._timeout = timeout_seconds
        self._today = today

    async def age_days(self, domain: str) -> int | None:
        name = registrable(domain)
        # Registro.br answers .br itself; rdap.org redirects to the authoritative registry.
        base = "https://rdap.registro.br" if name.endswith(".br") else "https://rdap.org"
        try:
            async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                response = await client.get(f"{base}/domain/{name}")
                response.raise_for_status()
                events = response.json().get("events", [])
        except (httpx.HTTPError, ValueError):
            return None
        registered = next((e["eventDate"] for e in events if e.get("eventAction") == "registration"), None)
        return _days_since(registered, self._today()) if registered else None


class CrtShClient:
    def __init__(self, timeout_seconds: float = 4.0, today: Today = date.today) -> None:
        self._timeout = timeout_seconds
        self._today = today

    async def certificate_age_days(self, domain: str) -> int | None:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get("https://crt.sh/", params={"q": registrable(domain), "output": "json"})
                response.raise_for_status()
                certificates = response.json()
        except (httpx.HTTPError, ValueError):
            return None
        starts = [c["not_before"] for c in certificates if c.get("not_before")]
        return _days_since(min(starts), self._today()) if starts else None


class RedisTrancoRanks:
    """Ranks loaded by the threat-intel-sync worker (hash domain -> position)."""

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    @classmethod
    def from_url(cls, redis_url: str) -> "RedisTrancoRanks":
        return cls(aioredis.from_url(redis_url, decode_responses=True))

    async def rank(self, domain: str) -> int | None:
        try:
            value = await self._redis.hget(TRANCO_KEY, registrable(domain))
        except aioredis.RedisError:
            return None
        return int(value) if value else None


class HttpDomainEvidenceClient:
    def __init__(self, rdap, crtsh, tranco) -> None:
        self._rdap = rdap
        self._crtsh = crtsh
        self._tranco = tranco

    async def lookup(self, domain: str) -> DomainEvidence:
        age, certificate, rank = await asyncio.gather(
            self._rdap.age_days(domain),
            self._crtsh.certificate_age_days(domain),
            self._tranco.rank(domain),
            return_exceptions=True,
        )
        # A source that crashed is unknown evidence, never a reason to trust the domain.
        return DomainEvidence(age_days=_known(age), certificate_age_days=_known(certificate), tranco_rank=_known(rank))


def _known(value: object) -> int | None:
    return value if isinstance(value, int) else None
