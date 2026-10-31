import asyncio
import logging
import time
from collections import Counter
from uuid import uuid4
from typing import AsyncIterator, Awaitable
from contracts import (
    StageEvent,
    StageName,
    StageStatus,
    ScanResponse,
    ScanDetails,
    Channel,
    ThreatLevel,
    TriageResult,
    Persuasion,
    ExtractResult,
    ImageSource,
    extract_domain,
    normalize_url,
)
from scan_orchestrator.domain.scan_input import ScanInput
from scan_orchestrator.domain.risk_score import RiskScore
from scan_orchestrator.domain.decision import ThresholdPolicy, decide, ocr_is_reliable
from scan_orchestrator.domain.verdict_catalog import verdict_message_for
from scan_orchestrator.domain.cascade import (
    BrandMatchUnavailable,
    BrandMatcherClientProtocol,
    Cascade,
    RedisCacheClientProtocol,
    StageContext,
    StageListener,
    TriageClient,
    elapsed_ms,
)
from scan_orchestrator.infrastructure.scan_repository import ScanRepository
from scan_orchestrator.infrastructure.image_extractor_client import ImageExtractorClientProtocol

logger = logging.getLogger("scan_orchestrator.analyze_text")


class StageProgress:
    """
    Merges stage reports from several parallel runs (a text with two links runs the
    cascade twice) into a single SSE stream: each stage is announced as started once,
    completed when no run still has it in progress, and skipped only if no run
    actually executed it.
    """

    def __init__(self) -> None:
        self._active: Counter[StageName] = Counter()
        self._emitted: set[tuple[StageName, StageStatus]] = set()

    def update(self, stage: StageName, status: StageStatus) -> list[StageEvent]:
        if status == "started":
            self._active[stage] += 1
        elif status == "done":
            self._active[stage] = max(0, self._active[stage] - 1)
            if self._active[stage] > 0:
                return []
        elif (stage, "started") in self._emitted:
            return []

        if (stage, status) in self._emitted:
            return []
        self._emitted.add((stage, status))
        return [StageEvent(stage=stage, status=status)]


class _EventPump:
    """Runs the analysis in the background and forwards stage events as they happen."""

    def __init__(self) -> None:
        self._progress = StageProgress()
        self._queue: asyncio.Queue[StageEvent] = asyncio.Queue()
        self.result: ScanResponse | None = None

    def report(self, stage: StageName, status: StageStatus) -> None:
        for event in self._progress.update(stage, status):
            self._queue.put_nowait(event)

    async def drive(self, work: Awaitable[ScanResponse]) -> AsyncIterator[StageEvent]:
        task = asyncio.ensure_future(work)
        try:
            while not task.done() or not self._queue.empty():
                if not self._queue.empty():
                    yield self._queue.get_nowait()
                    continue
                getter = asyncio.ensure_future(self._queue.get())
                done, _ = await asyncio.wait({task, getter}, return_when=asyncio.FIRST_COMPLETED)
                if getter in done:
                    yield getter.result()
                else:
                    getter.cancel()
        finally:
            if not task.done():
                task.cancel()
        self.result = task.result()


class AnalyzeTextUseCase:
    """
    Use case that orchestrates the multimodal cascade analysis (text, URL and image).
    Emits an async event stream (stage progress and final verdict) that feeds both
    synchronous REST endpoints and Server-Sent Events (SSE) in a unified way.
    """

    def __init__(
        self,
        triage_client: TriageClient,
        repository: ScanRepository,
        policy: ThresholdPolicy,
        cascade: Cascade | None = None,
        image_extractor: ImageExtractorClientProtocol | None = None,
        redis_client: RedisCacheClientProtocol | None = None,
        brand_matcher: BrandMatcherClientProtocol | None = None,
    ):
        self._triage_client = triage_client
        self._repository = repository
        self._policy = policy
        self._cascade = cascade
        self._image_extractor = image_extractor
        self._redis_client = redis_client
        self._brand_matcher = brand_matcher

    async def execute(self, scan_input: ScanInput) -> AsyncIterator[StageEvent | ScanResponse]:
        pump = _EventPump()
        async for event in pump.drive(self._analyze(scan_input, pump.report)):
            yield event
        yield pump.result

    async def _analyze(self, scan_input: ScanInput, report: StageListener) -> ScanResponse:
        response = await self._route(scan_input, report)
        await self._repository.save(scan_input.sha256, response)
        return response

    async def _route(self, scan_input: ScanInput, report: StageListener) -> ScanResponse:
        if scan_input.is_image and self._image_extractor:
            return await self._analyze_image(scan_input.image_b64, report)
        if scan_input.is_url_only and self._cascade:
            return await self._cascade.run(StageContext(raw_url=scan_input.content.strip(), on_stage=report))
        if scan_input.has_links and self._cascade:
            return await self._analyze_text_with_links(scan_input, report)
        return await self._analyze_plain_text(scan_input, report)

    async def _triage(self, text: str, report: StageListener) -> TriageResult | None:
        report(StageName.TRIAGE, "started")
        try:
            return await self._triage_client.triage(text)
        finally:
            report(StageName.TRIAGE, "done")

    async def _triage_and_inspect(
        self, text: str, urls: list[str], report: StageListener
    ) -> tuple[TriageResult | None, list[ScanResponse]]:
        """Runs text triage (if any) and each link's cascade in parallel."""
        inspections = [self._cascade.run(StageContext(raw_url=url, on_stage=report)) for url in urls]
        if not text:
            return None, _scan_responses(await asyncio.gather(*inspections, return_exceptions=True))

        triage, *url_results = await asyncio.gather(self._triage(text, report), *inspections, return_exceptions=True)
        return (None if isinstance(triage, Exception) else triage), _scan_responses(url_results)

    # --- Image (screenshot) ---

    async def _analyze_image(self, image_b64: str, report: StageListener) -> ScanResponse:
        report(StageName.IMAGE_EXTRACTION, "started")
        started = time.perf_counter()
        extract = await self._image_extractor.extract(image_b64)
        report(StageName.IMAGE_EXTRACTION, "done")

        # Perceptual cache (pHash): an already analyzed screenshot returns in < 10ms.
        cached = await self._redis_client.get_cached_phash(extract.phash) if self._redis_client else None
        if cached:
            return cached

        response = await self._image_verdict(extract, elapsed_ms(started), report)
        if self._redis_client:
            await self._redis_client.set_cached_phash(extract.phash, response)
        return response

    async def _image_verdict(self, extract: ExtractResult, duration_ms: float, report: StageListener) -> ScanResponse:
        visual_checked = True
        try:
            spoofing = await self._brand_spoofing_verdict(extract, duration_ms, report)
        except BrandMatchUnavailable:
            spoofing, visual_checked = None, False
        if spoofing:
            return spoofing

        response = await self._read_image(extract, duration_ms, report)
        if response.threat_level is not ThreatLevel.SAFE:
            return response
        if not ocr_is_reliable(extract.ocr_confidence):
            return _unsure_verdict(response, "image_ocr_low_confidence")
        if not visual_checked:
            return _unsure_verdict(response, "image_visual_rag_unavailable")
        return response

    async def _read_image(self, extract: ExtractResult, duration_ms: float, report: StageListener) -> ScanResponse:
        if extract.urls_found and self._cascade:
            return await self._image_with_links_verdict(extract, duration_ms, report)
        if extract.extracted_text:
            return await self._image_text_verdict(extract.extracted_text, duration_ms, report)
        return _verdict(
            ThreatLevel.INCONCLUSIVE,
            None,
            ScanDetails(
                channel=Channel.IMAGE,
                deciding_stage="empty_ocr_and_qr",
                category="no_text_or_url_detected",
                scores={"is_phishing": 0.0},
                latency_breakdown={"image_processing": duration_ms},
            ),
        )

    async def _brand_spoofing_verdict(
        self, extract: ExtractResult, duration_ms: float, report: StageListener
    ) -> ScanResponse | None:
        """
        Visual RAG on the clean screenshot. Only with a visible link: without a domain, a real
        bank app screenshot would look exactly like an imitation.
        """
        if not (self._brand_matcher and extract.urls_found and extract.clean_image_b64):
            return None
        domain = extract_domain(normalize_url(extract.urls_found[0]))
        report(StageName.VISUAL_RAG, "started")
        try:
            # A person's screenshot: compared locally, never sent to a third-party VLM.
            match = await self._brand_matcher.match_brand(extract.clean_image_b64, domain, ImageSource.USER_IMAGE)
        finally:
            report(StageName.VISUAL_RAG, "done")
        if not match.is_spoofing:
            return None
        return _verdict(
            ThreatLevel.SCAM,
            None,
            ScanDetails(
                channel=Channel.IMAGE,
                deciding_stage="image_visual_rag_brand_spoofing",
                category="brand_spoofing",
                scores={"is_phishing": 1.0, "brand_spoofing": 1.0},
                domain_signals={"spoofed_brand": match.matched_brand or "", "official_domains": ", ".join(match.official_domains)},
                latency_breakdown={"image_processing": duration_ms},
            ),
        )

    async def _image_with_links_verdict(
        self, extract: ExtractResult, duration_ms: float, report: StageListener
    ) -> ScanResponse:
        triage, url_responses = await self._triage_and_inspect(extract.extracted_text, extract.urls_found, report)
        latency = {"image_and_urls": duration_ms}

        scam_url = _first_scam(url_responses)
        if scam_url:
            return _embedded_scam_verdict(scam_url, Channel.IMAGE, "image_url", latency)

        unverified = _has_unverified(url_responses, expected=len(extract.urls_found))
        score = RiskScore(triage.is_phishing if triage else 0.50)
        threat = decide(score, has_unverified_links=unverified, policy=self._policy)
        return _verdict(
            threat,
            triage.persuasion if triage else None,
            ScanDetails(
                channel=Channel.IMAGE,
                deciding_stage="image_ocr_and_urls",
                category=triage.persuasion.value if triage else None,
                scores={"is_phishing": score.value},
                links_not_inspected=unverified,
                latency_breakdown=latency,
            ),
        )

    async def _image_text_verdict(self, text: str, duration_ms: float, report: StageListener) -> ScanResponse:
        triage = await self._triage(text, report)
        latency = {"image_ocr": duration_ms}
        if triage is None:
            return _verdict(
                ThreatLevel.INCONCLUSIVE,
                None,
                ScanDetails(
                    channel=Channel.IMAGE,
                    deciding_stage="contingency_fallback",
                    category="ocr_triage_unavailable",
                    scores={"is_phishing": 0.50},
                    latency_breakdown=latency,
                ),
            )

        threat = decide(RiskScore(triage.is_phishing), has_unverified_links=False, policy=self._policy)
        return _verdict(
            threat,
            triage.persuasion,
            ScanDetails(
                channel=Channel.IMAGE,
                deciding_stage="image_ocr_triage",
                category=triage.persuasion.value,
                scores={"is_phishing": triage.is_phishing},
                latency_breakdown=latency,
            ),
        )

    # --- Text ---

    async def _analyze_text_with_links(self, scan_input: ScanInput, report: StageListener) -> ScanResponse:
        started = time.perf_counter()
        urls = scan_input.extract_urls()
        triage, url_responses = await self._triage_and_inspect(scan_input.content, urls, report)
        latency = {"combined_scan": elapsed_ms(started)}

        scam_url = _first_scam(url_responses)
        if scam_url:
            return _embedded_scam_verdict(scam_url, Channel.TEXT, "embedded_url", latency)
        if triage is None:
            return _text_triage_unavailable(links_not_inspected=True, latency=latency)

        unverified = _has_unverified(url_responses, expected=len(urls))
        threat = decide(RiskScore(triage.is_phishing), has_unverified_links=unverified, policy=self._policy)
        return _text_triage_verdict(threat, triage, "combined_text_and_urls", unverified, latency)

    async def _analyze_plain_text(self, scan_input: ScanInput, report: StageListener) -> ScanResponse:
        started = time.perf_counter()
        triage = await self._triage(scan_input.content, report)
        latency = {"triage": elapsed_ms(started)}

        if triage is None:
            return _text_triage_unavailable(links_not_inspected=scan_input.has_links, latency=latency)

        # No cascade wired: the links were never inspected.
        threat = decide(RiskScore(triage.is_phishing), has_unverified_links=scan_input.has_links, policy=self._policy)
        return _text_triage_verdict(threat, triage, "triage", scan_input.has_links, latency)


def _verdict(threat: ThreatLevel, persuasion: Persuasion | None, details: ScanDetails) -> ScanResponse:
    return ScanResponse(
        id=uuid4(),
        threat_level=threat,
        verdict_message=verdict_message_for(threat, persuasion, category=details.category),
        details=details,
    )


def _unsure_verdict(response: ScanResponse, deciding_stage: str) -> ScanResponse:
    details = response.details.model_copy(update={"deciding_stage": deciding_stage})
    return _verdict(ThreatLevel.INCONCLUSIVE, None, details)


def _scan_responses(results: list) -> list[ScanResponse]:
    # A crashed inspection still counts as an unverified link (see _has_unverified); log why.
    for failure in (r for r in results if isinstance(r, BaseException)):
        logger.warning("link inspection failed: %r", failure)
    return [r for r in results if isinstance(r, ScanResponse)]


def _first_scam(url_responses: list[ScanResponse]) -> ScanResponse | None:
    return next((u for u in url_responses if u.threat_level == ThreatLevel.SCAM), None)


def _has_unverified(url_responses: list[ScanResponse], expected: int) -> bool:
    # A crashed inspection returns nothing, so a missing response is an unverified link too.
    if len(url_responses) < expected:
        return True
    return any(u.threat_level in (ThreatLevel.INCONCLUSIVE, ThreatLevel.CAUTION) for u in url_responses)


def _embedded_scam_verdict(
    scam_url: ScanResponse, channel: Channel, stage_prefix: str, latency: dict[str, float]
) -> ScanResponse:
    """A single scam link condemns the whole message, regardless of the text triage."""
    return _verdict(
        ThreatLevel.SCAM,
        Persuasion.FINANCIAL_THREAT,
        ScanDetails(
            channel=channel,
            deciding_stage=f"{stage_prefix}:{scam_url.details.deciding_stage}",
            category="embedded_phishing_link",
            scores={"is_phishing": 1.0, "embedded_link_is_scam": 1.0},
            domain_signals=scam_url.details.domain_signals,
            links_not_inspected=False,
            latency_breakdown=latency,
        ),
    )


def _text_triage_unavailable(links_not_inspected: bool, latency: dict[str, float]) -> ScanResponse:
    return _verdict(
        ThreatLevel.INCONCLUSIVE,
        None,
        ScanDetails(
            channel=Channel.TEXT,
            deciding_stage="contingency_fallback",
            category="inspection_unavailable",
            scores={"is_phishing": 0.50},
            links_not_inspected=links_not_inspected,
            latency_breakdown=latency,
        ),
    )


def _text_triage_verdict(
    threat: ThreatLevel,
    triage: TriageResult,
    deciding_stage: str,
    links_not_inspected: bool,
    latency: dict[str, float],
) -> ScanResponse:
    return _verdict(
        threat,
        triage.persuasion,
        ScanDetails(
            channel=Channel.TEXT,
            deciding_stage=deciding_stage,
            category=triage.persuasion.value,
            scores={
                "is_phishing": triage.is_phishing,
                "requires_visual_inspection": triage.requires_visual_inspection,
            },
            links_not_inspected=links_not_inspected,
            latency_breakdown=latency,
        ),
    )
