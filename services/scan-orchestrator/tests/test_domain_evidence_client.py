from datetime import date

import fakeredis.aioredis
import httpx
import pytest
import respx

from scan_orchestrator.domain.domain_risk import DomainEvidence
from scan_orchestrator.infrastructure.domain_evidence_client import (
    CrtShClient,
    HttpDomainEvidenceClient,
    RdapClient,
    RedisTrancoRanks,
)

TODAY = date(2026, 10, 28)


def rdap_body(registered: str) -> dict:
    return {"events": [{"eventAction": "last changed", "eventDate": "2026-01-01T00:00:00Z"},
                       {"eventAction": "registration", "eventDate": registered}]}


async def test_rdap_uses_registro_br_for_br_domains_and_counts_days():
    async with respx.mock() as mock:
        mock.get("https://rdap.registro.br/domain/golpe.com.br").respond(json=rdap_body("2026-10-25T10:00:00Z"))
        assert await RdapClient(today=lambda: TODAY).age_days("www.golpe.com.br") == 3


async def test_rdap_uses_the_generic_bootstrap_for_other_domains():
    async with respx.mock() as mock:
        mock.get("https://rdap.org/domain/exemplo.com").respond(json=rdap_body("2016-10-28T00:00:00Z"))
        assert await RdapClient(today=lambda: TODAY).age_days("exemplo.com") == 3652


@pytest.mark.parametrize("reply", [httpx.Response(404), httpx.Response(200, json={"events": []}), httpx.ConnectTimeout("lento")])
async def test_rdap_failure_means_unknown(reply):
    async with respx.mock() as mock:
        route = mock.get("https://rdap.org/domain/exemplo.com")
        route.mock(side_effect=reply) if isinstance(reply, Exception) else route.mock(return_value=reply)
        assert await RdapClient(today=lambda: TODAY).age_days("exemplo.com") is None


async def test_crtsh_takes_the_oldest_certificate():
    certs = [{"not_before": "2026-10-20T00:00:00"}, {"not_before": "2026-10-26T12:00:00"}]
    async with respx.mock() as mock:
        mock.get("https://crt.sh/", params={"q": "golpe.com", "output": "json"}).respond(json=certs)
        assert await CrtShClient(today=lambda: TODAY).certificate_age_days("golpe.com") == 8


async def test_crtsh_without_certificates_is_unknown():
    async with respx.mock() as mock:
        mock.get("https://crt.sh/", params={"q": "golpe.com", "output": "json"}).respond(json=[])
        assert await CrtShClient(today=lambda: TODAY).certificate_age_days("golpe.com") is None


async def test_tranco_rank_is_read_for_the_registrable_domain():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    await redis.hset("tranco:rank", mapping={"google.com": 1})
    ranks = RedisTrancoRanks(redis)
    assert await ranks.rank("mail.google.com") == 1
    assert await ranks.rank("desconhecido.com") is None


class Fixed:
    def __init__(self, value):
        self.value = value

    async def age_days(self, domain):
        return self.value

    async def certificate_age_days(self, domain):
        return self.value

    async def rank(self, domain):
        return self.value


class Broken:
    async def age_days(self, domain):
        raise RuntimeError("down")


async def test_client_combines_the_three_sources():
    client = HttpDomainEvidenceClient(rdap=Fixed(10), crtsh=Fixed(8), tranco=Fixed(None))
    assert await client.lookup("x.com") == DomainEvidence(age_days=10, certificate_age_days=8, tranco_rank=None)


async def test_one_broken_source_does_not_hide_the_others():
    client = HttpDomainEvidenceClient(rdap=Broken(), crtsh=Fixed(8), tranco=Fixed(42))
    assert await client.lookup("x.com") == DomainEvidence(age_days=None, certificate_age_days=8, tranco_rank=42)
