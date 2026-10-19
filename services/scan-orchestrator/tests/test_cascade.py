import pytest
from contracts import ThreatLevel, InspectResult, TriageResult, Persuasion
from scan_orchestrator.domain.decision import ThresholdPolicy
from scan_orchestrator.domain.cascade import (
    StageContext,
    Cascade,
    Stage0CacheAndFeeds,
    Stage1ReputationAndSignals,
    Stage2RemoteInspection,
)
from scan_orchestrator.infrastructure.fakes import (
    FakeRedisCacheClient,
    FakeReputationClient,
    FakeInspectorClient,
    FakeTriageClient,
)


@pytest.fixture
def policy():
    return ThresholdPolicy(scam=0.70, safe=0.30)


@pytest.fixture
def fake_redis():
    return FakeRedisCacheClient()


@pytest.fixture
def fake_reputation():
    return FakeReputationClient()


@pytest.fixture
def fake_inspector():
    return FakeInspectorClient()


@pytest.fixture
def fake_triage():
    return FakeTriageClient()


@pytest.fixture
def cascade(fake_redis, fake_reputation, fake_inspector, fake_triage, policy):
    stage0 = Stage0CacheAndFeeds(cache_client=fake_redis)
    stage1 = Stage1ReputationAndSignals(reputation_client=fake_reputation)
    stage2 = Stage2RemoteInspection(
        inspector_client=fake_inspector,
        triage_client=fake_triage,
    )
    return Cascade(stages=[stage0, stage1, stage2], policy=policy)


@pytest.mark.asyncio
async def test_stage0_blacklist_feed_short_circuit(cascade, fake_redis):
    # Simulates a URL present in the OpenPhish/URLhaus feed
    target_url = "https://phish-banco-falso.com/login"
    fake_redis.add_to_blacklist(target_url)

    ctx = StageContext(raw_url=target_url)
    res = await cascade.run(ctx)

    assert res.threat_level == ThreatLevel.SCAM
    assert res.details.deciding_stage == "stage_0_blacklist_feed"
    assert res.details.scores["is_phishing"] == 1.0


@pytest.mark.asyncio
async def test_stage2_antibot_ethical_fallback_returns_inconclusive(cascade, fake_inspector):
    target_url = "https://site-protegido-cloudflare.com"
    fake_inspector.set_result(
        target_url,
        InspectResult(
            final_url=target_url,
            is_blocked=True,
            blocked_reason="cloudflare_challenge",
        ),
    )

    ctx = StageContext(raw_url=target_url)
    res = await cascade.run(ctx)

    # ETHICAL RULE: an anti-bot block NEVER returns SEGURO, always INCONCLUSIVO
    assert res.threat_level == ThreatLevel.INCONCLUSIVE
    assert res.details.deciding_stage == "stage_2_antibot_or_error"
    assert res.details.links_not_inspected is True


@pytest.mark.asyncio
async def test_stage2_credential_harvesting_detected(cascade, fake_inspector, fake_triage):
    target_url = "https://recadastro-beneficio.top/entrar"
    fake_inspector.set_result(
        target_url,
        InspectResult(
            dom_text="Digite sua senha e dados do cartão para atualizar seu benefício",
            final_url=target_url,
            has_password_field=True,
            is_blocked=False,
        ),
    )
    fake_triage.set_result(
        TriageResult(
            is_phishing=0.92,
            requires_visual_inspection=0.0,
            persuasion=Persuasion.FINANCIAL_THREAT,
        )
    )

    ctx = StageContext(raw_url=target_url)
    res = await cascade.run(ctx)

    assert res.threat_level == ThreatLevel.SCAM
    assert res.details.deciding_stage == "stage_2_inspection"
    assert res.details.scores["is_phishing"] >= 0.90


@pytest.mark.asyncio
async def test_stage2_legitimate_url_returns_safe(cascade, fake_inspector, fake_triage):
    target_url = "https://minha-loja-legitima.com.br"
    fake_inspector.set_result(
        target_url,
        InspectResult(
            dom_text="Bem-vindo à nossa loja de roupas artesanais feitas à mão.",
            final_url=target_url,
            has_password_field=False,
            is_blocked=False,
        ),
    )
    fake_triage.set_result(
        TriageResult(
            is_phishing=0.05,
            requires_visual_inspection=0.0,
            persuasion=Persuasion.NONE,
        )
    )

    ctx = StageContext(raw_url=target_url)
    res = await cascade.run(ctx)

    assert res.threat_level == ThreatLevel.SAFE
    assert res.details.deciding_stage == "stage_2_inspection"
    assert res.details.scores["is_phishing"] <= 0.30


@pytest.mark.asyncio
async def test_stage2_visual_rag_brand_spoofing_short_circuit(
    fake_redis, fake_reputation, fake_inspector, fake_triage, policy
):
    from contracts import BrandMatchResult
    from scan_orchestrator.infrastructure.fakes import FakeBrandMatcherClient

    fake_brand_matcher = FakeBrandMatcherClient(
        default_result=BrandMatchResult(
            matched_brand="Banco do Brasil",
            is_spoofing=True,
            similarity=0.95,
            official_domains=["bb.com.br", "bancodobrasil.com.br"],
        )
    )

    stage0 = Stage0CacheAndFeeds(cache_client=fake_redis)
    stage1 = Stage1ReputationAndSignals(reputation_client=fake_reputation)
    stage2 = Stage2RemoteInspection(
        inspector_client=fake_inspector,
        triage_client=fake_triage,
        brand_matcher=fake_brand_matcher,
    )
    cascade = Cascade(stages=[stage0, stage1, stage2], policy=policy)

    target_url = "https://bb-seguro-atualizacao.xyz/entrar"
    fake_inspector.set_result(
        target_url,
        InspectResult(
            dom_text="Acesse sua conta",
            final_url=target_url,
            screenshot_b64="fake_screenshot_with_bb_logo",
            is_blocked=False,
        ),
    )

    ctx = StageContext(raw_url=target_url)
    res = await cascade.run(ctx)

    assert res.threat_level == ThreatLevel.SCAM
    assert res.details.deciding_stage == "visual_rag_brand_spoofing"
    assert res.details.category == "brand_spoofing"
    assert res.details.scores["brand_spoofing"] == 1.0
    assert res.details.domain_signals["spoofed_brand"] == "Banco do Brasil"
