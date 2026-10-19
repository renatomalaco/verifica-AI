from contracts import BrandMatchResult, InspectResult, Persuasion, TriageResult
from scan_orchestrator.domain import cascade
from scan_orchestrator.infrastructure.fakes import (
    FakeBrandMatcherClient,
    FakeInspectorClient,
    FakeRedisCacheClient,
    FakeReputationClient,
    FakeTriageClient,
)


def test_domain_cascade_has_no_fakes():
    assert [name for name in vars(cascade) if name.startswith("Fake")] == []


async def test_fakes_work_without_arguments():
    assert await FakeRedisCacheClient().is_blacklisted("https://exemplo.com") is False
    assert await FakeReputationClient().get_domain_signals("exemplo.com") == {"age": "unknown", "reputation": "neutral"}
    assert await FakeInspectorClient().inspect("https://exemplo.com") == InspectResult()
    assert await FakeBrandMatcherClient().match_brand("img") == BrandMatchResult()
    assert await FakeTriageClient().triage("oi") == TriageResult(is_phishing=0.1, persuasion=Persuasion.NONE)
