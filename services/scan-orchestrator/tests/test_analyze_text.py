import pytest
from contracts import ThreatLevel, Channel, Persuasion, StageEvent, ScanResponse, TriageResult, VerdictMessage
from scan_orchestrator.domain.scan_input import ScanInput
from scan_orchestrator.domain.decision import ThresholdPolicy
from scan_orchestrator.infrastructure.scan_repository import InMemoryScanRepository
from scan_orchestrator.application.analyze_text import AnalyzeTextUseCase


class FakeTriageClient:
    def __init__(self, result: TriageResult | None = None):
        self.result = result
        self.call_count = 0

    async def triage(self, text: str) -> TriageResult | None:
        self.call_count += 1
        return self.result


@pytest.mark.asyncio
async def test_analyze_text_emits_events_and_final_verdict():
    triage_client = FakeTriageClient(
        result=TriageResult(
            is_phishing=0.96,
            requires_visual_inspection=0.0,
            persuasion=Persuasion.AFFECTIVE_COERCION,
        )
    )
    repo = InMemoryScanRepository()
    use_case = AnalyzeTextUseCase(
        triage_client=triage_client,
        repository=repo,
        policy=ThresholdPolicy(scam=0.90, safe=0.10),
    )

    scan_input = ScanInput(content="Oi mãe, troquei de número, me faz um pix urgente")
    events = [item async for item in use_case.execute(scan_input)]

    assert isinstance(events[0], StageEvent)
    assert events[0].stage == "triage"
    assert events[0].status == "started"

    assert isinstance(events[1], StageEvent)
    assert events[1].stage == "triage"
    assert events[1].status == "done"

    response = events[2]
    assert isinstance(response, ScanResponse)
    assert response.threat_level == ThreatLevel.SCAM
    assert response.details.channel == Channel.TEXT
    assert "triage" in response.details.latency_breakdown
    assert response.details.latency_breakdown["triage"] >= 0.0

    assert scan_input.sha256 in repo.records
    assert len(repo.records[scan_input.sha256]) == 1


@pytest.mark.asyncio
async def test_analyze_text_contingency_when_triage_fails():
    triage_client = FakeTriageClient(result=None)
    repo = InMemoryScanRepository()
    use_case = AnalyzeTextUseCase(
        triage_client=triage_client,
        repository=repo,
        policy=ThresholdPolicy(scam=0.90, safe=0.10),
    )

    scan_input = ScanInput(content="Texto qualquer para teste")
    events = [item async for item in use_case.execute(scan_input)]

    response = events[-1]
    assert isinstance(response, ScanResponse)
    assert response.threat_level == ThreatLevel.INCONCLUSIVE
    assert response.verdict_message is VerdictMessage.INCONCLUSIVE


@pytest.mark.asyncio
async def test_analyze_url_only_triggers_cascade():
    from scan_orchestrator.domain.cascade import Cascade, Stage0CacheAndFeeds
    from scan_orchestrator.infrastructure.fakes import FakeRedisCacheClient

    fake_redis = FakeRedisCacheClient()
    fake_redis.add_to_blacklist("https://phish.com/login")
    cascade = Cascade(
        stages=[Stage0CacheAndFeeds(fake_redis)],
        policy=ThresholdPolicy(scam=0.90, safe=0.10),
    )

    repo = InMemoryScanRepository()
    use_case = AnalyzeTextUseCase(
        triage_client=FakeTriageClient(result=None),
        repository=repo,
        policy=ThresholdPolicy(scam=0.90, safe=0.10),
        cascade=cascade,
    )

    scan_input = ScanInput(content="https://phish.com/login")
    events = [item async for item in use_case.execute(scan_input)]

    response = events[-1]
    assert isinstance(response, ScanResponse)
    assert response.threat_level == ThreatLevel.SCAM
    assert response.details.channel == Channel.URL
    assert response.details.deciding_stage == "stage_0_blacklist_feed"


@pytest.mark.asyncio
async def test_analyze_text_with_embedded_phishing_link_marks_scam():
    from scan_orchestrator.domain.cascade import Cascade, Stage0CacheAndFeeds
    from scan_orchestrator.infrastructure.fakes import FakeRedisCacheClient

    fake_redis = FakeRedisCacheClient()
    fake_redis.add_to_blacklist("https://phish.com/premio")
    cascade = Cascade(
        stages=[Stage0CacheAndFeeds(fake_redis)],
        policy=ThresholdPolicy(scam=0.90, safe=0.10),
    )

    # Seemingly neutral text, but the link is a scam
    triage_client = FakeTriageClient(
        result=TriageResult(is_phishing=0.10, persuasion=Persuasion.NONE)
    )
    repo = InMemoryScanRepository()
    use_case = AnalyzeTextUseCase(
        triage_client=triage_client,
        repository=repo,
        policy=ThresholdPolicy(scam=0.90, safe=0.10),
        cascade=cascade,
    )

    scan_input = ScanInput(content="Veja as novidades da loja no link https://phish.com/premio agora")
    events = [item async for item in use_case.execute(scan_input)]

    response = events[-1]
    assert isinstance(response, ScanResponse)
    assert response.threat_level == ThreatLevel.SCAM
    assert response.details.channel == Channel.TEXT
    assert "https://phish.com/premio" in str(response.details.domain_signals or "") or response.details.scores.get("embedded_link_is_scam") == 1.0


@pytest.mark.asyncio
async def test_analyze_image_with_phishing_qr_code_marks_scam():
    from contracts import ExtractResult
    from scan_orchestrator.domain.cascade import Cascade, Stage0CacheAndFeeds
    from scan_orchestrator.infrastructure.fakes import FakeRedisCacheClient
    from scan_orchestrator.infrastructure.image_extractor_client import FakeImageExtractorClient

    fake_redis = FakeRedisCacheClient()
    fake_redis.add_to_blacklist("https://phish-qr.top/pix")
    cascade = Cascade(
        stages=[Stage0CacheAndFeeds(fake_redis)],
        policy=ThresholdPolicy(scam=0.90, safe=0.10),
    )

    image_client = FakeImageExtractorClient(
        default_result=ExtractResult(
            sha256="image_sha256",
            phash="0123456789abcdef",
            extracted_text="Pague agora com QR Code abaixo",
            qr_codes=["https://phish-qr.top/pix"],
            urls_found=["https://phish-qr.top/pix"],
        )
    )

    repo = InMemoryScanRepository()
    use_case = AnalyzeTextUseCase(
        triage_client=FakeTriageClient(result=None),
        repository=repo,
        policy=ThresholdPolicy(scam=0.90, safe=0.10),
        cascade=cascade,
        image_extractor=image_client,
        redis_client=fake_redis,
    )

    scan_input = ScanInput(image_b64="valid_sample_image_base64_data")
    events = [item async for item in use_case.execute(scan_input)]

    response = events[-1]
    assert isinstance(response, ScanResponse)
    assert response.threat_level == ThreatLevel.SCAM
    assert response.details.channel == Channel.IMAGE
    assert "image_extraction" in [e.stage for e in events if isinstance(e, StageEvent)]


@pytest.mark.asyncio
async def test_analyze_image_phash_cache_hit():
    from contracts import ExtractResult, ScanDetails
    from scan_orchestrator.infrastructure.fakes import FakeRedisCacheClient
    from scan_orchestrator.infrastructure.image_extractor_client import FakeImageExtractorClient
    from uuid import uuid4

    fake_redis = FakeRedisCacheClient()
    cached_response = ScanResponse(
        id=uuid4(),
        threat_level=ThreatLevel.SCAM,
        verdict_message=VerdictMessage.SCAM_FINANCIAL_THREAT,
        details=ScanDetails(
            channel=Channel.IMAGE,
            deciding_stage="phash_cache",
            scores={"is_phishing": 1.0},
        ),
    )
    await fake_redis.set_cached_phash("a1b2c3d4e5f60718", cached_response)

    image_client = FakeImageExtractorClient(
        default_result=ExtractResult(
            sha256="new_image_sha",
            phash="a1b2c3d4e5f60718",
            extracted_text="",
            qr_codes=[],
            urls_found=[],
        )
    )

    repo = InMemoryScanRepository()
    use_case = AnalyzeTextUseCase(
        triage_client=FakeTriageClient(result=None),
        repository=repo,
        policy=ThresholdPolicy(scam=0.90, safe=0.10),
        image_extractor=image_client,
        redis_client=fake_redis,
    )

    scan_input = ScanInput(image_b64="sample_compressed_whatsapp_print")
    events = [item async for item in use_case.execute(scan_input)]

    response = events[-1]
    assert isinstance(response, ScanResponse)
    assert response.threat_level == ThreatLevel.SCAM
    assert response.details.deciding_stage == "phash_cache"


# --- Ethics rule: only links nobody could verify cap the verdict at CUIDADO ---

def _url_verdict(threat: ThreatLevel) -> ScanResponse:
    from uuid import uuid4
    from contracts import ScanDetails

    return ScanResponse(
        id=uuid4(),
        threat_level=threat,
        verdict_message=VerdictMessage.SAFE,
        details=ScanDetails(channel=Channel.URL, deciding_stage="stage_2_inspection"),
    )


class ScriptedCascade:
    """Returns one scripted outcome per URL, in order; an exception means the inspection crashed."""

    def __init__(self, outcomes: list):
        self._outcomes = list(outcomes)

    async def run(self, ctx):
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


async def _verdict_for(text: str, cascade: ScriptedCascade) -> ScanResponse:
    use_case = AnalyzeTextUseCase(
        triage_client=FakeTriageClient(result=TriageResult(is_phishing=0.02, persuasion=Persuasion.NONE)),
        repository=InMemoryScanRepository(),
        policy=ThresholdPolicy(scam=0.90, safe=0.10),
        cascade=cascade,
    )
    events = [item async for item in use_case.execute(ScanInput(content=text))]
    return events[-1]


async def test_text_with_inspected_safe_link_can_be_safe():
    response = await _verdict_for(
        "Seu pedido saiu para entrega: https://loja.example/pedido",
        ScriptedCascade([_url_verdict(ThreatLevel.SAFE)]),
    )
    assert response.threat_level is ThreatLevel.SAFE
    assert response.details.links_not_inspected is False


async def test_text_with_inconclusive_link_stays_at_caution():
    response = await _verdict_for(
        "Confira aqui: https://loja.example/pedido",
        ScriptedCascade([_url_verdict(ThreatLevel.INCONCLUSIVE)]),
    )
    assert response.threat_level is ThreatLevel.CAUTION
    assert response.details.links_not_inspected is True


async def test_a_link_whose_inspection_crashed_counts_as_unverified():
    response = await _verdict_for(
        "Dois links: https://a.example/x e https://b.example/y",
        ScriptedCascade([_url_verdict(ThreatLevel.SAFE), RuntimeError("inspector down")]),
    )
    assert response.threat_level is ThreatLevel.CAUTION
    assert response.details.links_not_inspected is True


async def test_a_crashed_link_inspection_is_logged_not_swallowed(caplog):
    with caplog.at_level("WARNING", logger="scan_orchestrator.analyze_text"):
        await _verdict_for(
            "Veja: https://a.example/x",
            ScriptedCascade([RuntimeError("inspector down")]),
        )
    assert "inspector down" in caplog.text


# --- Image: an unsure OCR never leads to SEGURO ---

async def _image_verdict(ocr_confidence: float | None) -> ScanResponse:
    from contracts import ExtractResult
    from scan_orchestrator.infrastructure.image_extractor_client import FakeImageExtractorClient

    extractor = FakeImageExtractorClient(
        default_result=ExtractResult(
            sha256="s", phash="0123456789abcdef", extracted_text="bom dia, tudo certo", ocr_confidence=ocr_confidence
        )
    )
    use_case = AnalyzeTextUseCase(
        triage_client=FakeTriageClient(result=TriageResult(is_phishing=0.02, persuasion=Persuasion.NONE)),
        repository=InMemoryScanRepository(),
        policy=ThresholdPolicy(scam=0.90, safe=0.10),
        image_extractor=extractor,
    )
    events = [item async for item in use_case.execute(ScanInput(image_b64="img"))]
    return events[-1]


async def test_well_read_image_with_harmless_text_can_be_safe():
    assert (await _image_verdict(ocr_confidence=92.0)).threat_level is ThreatLevel.SAFE


@pytest.mark.parametrize("confidence", [35.0, None])
async def test_poorly_read_image_is_inconclusive_instead_of_safe(confidence):
    response = await _image_verdict(ocr_confidence=confidence)
    assert response.threat_level is ThreatLevel.INCONCLUSIVE
    assert response.details.deciding_stage == "image_ocr_low_confidence"


# --- Image: the clean screenshot goes to Visual RAG when a link shows the domain ---

class RecordingBrandMatcher:
    def __init__(self, spoofing: bool):
        self.spoofing = spoofing
        self.calls: list[tuple[str, str | None]] = []

    async def match_brand(self, image_b64: str, current_domain: str | None = None):
        from contracts import BrandMatchResult

        self.calls.append((image_b64, current_domain))
        return BrandMatchResult(matched_brand="Itaú Unibanco", is_spoofing=self.spoofing, similarity=0.97,
                                official_domains=["itau.com.br"])


async def _image_with_matcher(urls: list[str], matcher: RecordingBrandMatcher) -> ScanResponse:
    from contracts import ExtractResult
    from scan_orchestrator.domain.cascade import Cascade
    from scan_orchestrator.infrastructure.image_extractor_client import FakeImageExtractorClient

    extractor = FakeImageExtractorClient(default_result=ExtractResult(
        sha256="s", phash="0123456789abcdef", extracted_text="Atualize seu cadastro", urls_found=urls,
        ocr_confidence=90.0, clean_image_b64="CLEAN",
    ))
    use_case = AnalyzeTextUseCase(
        triage_client=FakeTriageClient(result=TriageResult(is_phishing=0.2, persuasion=Persuasion.NONE)),
        repository=InMemoryScanRepository(),
        policy=ThresholdPolicy(scam=0.90, safe=0.10),
        cascade=Cascade(stages=[], policy=ThresholdPolicy(scam=0.90, safe=0.10)),
        image_extractor=extractor,
        brand_matcher=matcher,
    )
    events = [item async for item in use_case.execute(ScanInput(image_b64="ORIGINAL"))]
    return events[-1]


async def test_screenshot_imitating_a_bank_on_another_domain_is_a_scam():
    matcher = RecordingBrandMatcher(spoofing=True)
    response = await _image_with_matcher(["https://itau-atualiza.top/login"], matcher)

    assert response.threat_level is ThreatLevel.SCAM
    assert response.details.deciding_stage == "image_visual_rag_brand_spoofing"
    # Only the clean copy (no EXIF) leaves the extractor.
    assert matcher.calls == [("CLEAN", "itau-atualiza.top")]


async def test_screenshot_without_a_visible_link_is_not_compared_to_brands():
    matcher = RecordingBrandMatcher(spoofing=True)
    await _image_with_matcher([], matcher)
    assert matcher.calls == []
