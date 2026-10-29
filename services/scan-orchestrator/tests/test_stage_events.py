from contracts import (
    BrandMatchResult,
    ExtractResult,
    InspectResult,
    Persuasion,
    ScanResponse,
    StageEvent,
    StageName,
    TriageResult,
)
from scan_orchestrator.application.analyze_text import AnalyzeTextUseCase, StageProgress
from scan_orchestrator.domain.cascade import (
    Cascade,
    Stage0CacheAndFeeds,
    Stage1ReputationAndSignals,
    Stage2RemoteInspection,
    StageContext,
)
from scan_orchestrator.infrastructure.fakes import (
    FakeBrandMatcherClient,
    FakeInspectorClient,
    FakeRedisCacheClient,
    FakeDomainEvidenceClient,
    FakeTriageClient,
)
from scan_orchestrator.domain.decision import ThresholdPolicy
from scan_orchestrator.domain.scan_input import ScanInput
from scan_orchestrator.infrastructure.image_extractor_client import FakeImageExtractorClient
from scan_orchestrator.infrastructure.scan_repository import InMemoryScanRepository

POLICY = ThresholdPolicy(scam=0.90, safe=0.10)


def build_cascade(redis=None, inspector=None, brand_matcher=None) -> Cascade:
    return Cascade(
        stages=[
            Stage0CacheAndFeeds(cache_client=redis or FakeRedisCacheClient()),
            Stage1ReputationAndSignals(evidence_client=FakeDomainEvidenceClient()),
            Stage2RemoteInspection(
                inspector_client=inspector or FakeInspectorClient(),
                triage_client=FakeTriageClient(),
                brand_matcher=brand_matcher,
            ),
        ],
        policy=POLICY,
    )


def stage_events(items) -> list[tuple[str, str]]:
    return [(e.stage.value, e.status) for e in items if isinstance(e, StageEvent)]


# --- Cascade ---

async def test_cascade_reports_each_stage_it_runs():
    seen: list[tuple[str, str]] = []
    ctx = StageContext(raw_url="https://loja-legitima.com.br", on_stage=lambda s, st: seen.append((s.value, st)))

    await build_cascade().run(ctx)

    assert seen == [
        ("stage_0_cache", "started"),
        ("stage_0_cache", "done"),
        ("stage_1_signals", "started"),
        ("stage_1_signals", "done"),
        ("stage_2_inspection", "started"),
        ("stage_2_inspection", "done"),
    ]


async def test_cascade_marks_remaining_stages_as_skipped_after_short_circuit():
    redis = FakeRedisCacheClient()
    redis.add_to_blacklist("https://phish.com/login")
    seen: list[tuple[str, str]] = []
    ctx = StageContext(raw_url="https://phish.com/login", on_stage=lambda s, st: seen.append((s.value, st)))

    await build_cascade(redis=redis).run(ctx)

    assert seen == [
        ("stage_0_cache", "started"),
        ("stage_0_cache", "done"),
        ("stage_1_signals", "skipped"),
        ("stage_2_inspection", "skipped"),
    ]


async def test_stage2_reports_visual_rag_when_comparing_logos():
    url = "https://bb-seguro.xyz/entrar"
    inspector = FakeInspectorClient()
    inspector.set_result(url, InspectResult(dom_text="Entre", final_url=url, screenshot_b64="png"))
    matcher = FakeBrandMatcherClient(BrandMatchResult(matched_brand="BB", is_spoofing=True, similarity=0.9))
    seen: list[tuple[str, str]] = []
    ctx = StageContext(raw_url=url, on_stage=lambda s, st: seen.append((s.value, st)))

    await build_cascade(inspector=inspector, brand_matcher=matcher).run(ctx)

    assert ("visual_rag", "started") in seen
    assert ("visual_rag", "done") in seen
    assert seen[-1] == ("stage_2_inspection", "done")


async def test_cascade_without_listener_still_works():
    res = await build_cascade().run(StageContext(raw_url="https://example.com"))
    assert isinstance(res, ScanResponse)


# --- Aggregating several links in parallel ---

def test_stage_progress_merges_parallel_runs_of_the_same_stage():
    progress = StageProgress()
    out = []
    out += progress.update(StageName.STAGE_0_CACHE, "started")
    out += progress.update(StageName.STAGE_0_CACHE, "started")
    out += progress.update(StageName.STAGE_0_CACHE, "done")
    out += progress.update(StageName.STAGE_0_CACHE, "done")
    assert [(e.stage.value, e.status) for e in out] == [("stage_0_cache", "started"), ("stage_0_cache", "done")]


def test_stage_progress_does_not_mark_skipped_a_stage_another_link_ran():
    progress = StageProgress()
    out = []
    out += progress.update(StageName.STAGE_2_INSPECTION, "started")
    out += progress.update(StageName.STAGE_2_INSPECTION, "skipped")
    out += progress.update(StageName.STAGE_2_INSPECTION, "done")
    out += progress.update(StageName.STAGE_1_SIGNALS, "skipped")
    out += progress.update(StageName.STAGE_1_SIGNALS, "skipped")
    assert [(e.stage.value, e.status) for e in out] == [
        ("stage_2_inspection", "started"),
        ("stage_2_inspection", "done"),
        ("stage_1_signals", "skipped"),
    ]


# --- Use case (what reaches the SSE) ---

async def test_url_only_scan_streams_real_cascade_stages():
    use_case = AnalyzeTextUseCase(
        triage_client=FakeTriageClient(),
        repository=InMemoryScanRepository(),
        policy=POLICY,
        cascade=build_cascade(),
    )

    items = [i async for i in use_case.execute(ScanInput(content="https://loja-legitima.com.br"))]

    assert stage_events(items) == [
        ("stage_0_cache", "started"),
        ("stage_0_cache", "done"),
        ("stage_1_signals", "started"),
        ("stage_1_signals", "done"),
        ("stage_2_inspection", "started"),
        ("stage_2_inspection", "done"),
    ]
    assert isinstance(items[-1], ScanResponse)


async def test_text_with_links_streams_triage_and_cascade_stages():
    use_case = AnalyzeTextUseCase(
        triage_client=FakeTriageClient(TriageResult(is_phishing=0.2, persuasion=Persuasion.NONE)),
        repository=InMemoryScanRepository(),
        policy=POLICY,
        cascade=build_cascade(),
    )

    items = [i async for i in use_case.execute(ScanInput(content="Olha https://a.com.br e https://b.com.br"))]
    events = stage_events(items)

    assert events[0] == ("triage", "started")
    for stage in ("triage", "stage_0_cache", "stage_1_signals", "stage_2_inspection"):
        assert (stage, "done") in events
    # Each stage appears once per status, even with two links in parallel.
    assert len(events) == len(set(events))
    assert isinstance(items[-1], ScanResponse)


async def test_image_with_link_streams_extraction_triage_and_cascade():
    extractor = FakeImageExtractorClient(
        default_result=ExtractResult(
            sha256="s",
            phash="p",
            extracted_text="Pague o boleto",
            urls_found=["https://boleto.top/pagar"],
        )
    )
    use_case = AnalyzeTextUseCase(
        triage_client=FakeTriageClient(),
        repository=InMemoryScanRepository(),
        policy=POLICY,
        cascade=build_cascade(),
        image_extractor=extractor,
        redis_client=FakeRedisCacheClient(),
    )

    items = [i async for i in use_case.execute(ScanInput(image_b64="aW1n"))]
    events = stage_events(items)

    assert events[:2] == [("image_extraction", "started"), ("image_extraction", "done")]
    assert ("triage", "done") in events
    assert ("stage_2_inspection", "done") in events
    assert isinstance(items[-1], ScanResponse)


async def test_scan_is_retrievable_by_id_after_analysis():
    repo = InMemoryScanRepository()
    use_case = AnalyzeTextUseCase(triage_client=FakeTriageClient(), repository=repo, policy=POLICY)

    items = [i async for i in use_case.execute(ScanInput(content="Bom dia, tudo bem?"))]
    response = items[-1]

    assert await repo.get(response.id) == response
