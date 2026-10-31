import time
from typing import Callable, Protocol
from uuid import uuid4
from contracts import (
    ThreatLevel,
    Channel,
    ScanResponse,
    ScanDetails,
    InspectResult,
    TriageResult,
    Persuasion,
    BrandMatchResult,
    ImageSource,
    StageName,
    StageStatus,
    normalize_url,
    extract_domain,
)
from scan_orchestrator.domain.risk_score import RiskScore
from scan_orchestrator.domain.decision import ThresholdPolicy, decide
from contracts.protected_brands import protected_domains
from scan_orchestrator.domain.domain_risk import DomainAssessment, DomainEvidence, assess_domain
from scan_orchestrator.domain.lookalike import find_imitated_domain
from scan_orchestrator.domain.verdict_catalog import verdict_message_for


StageListener = Callable[[StageName, StageStatus], None]


def elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)


class StageContext:
    def __init__(self, raw_url: str, on_stage: StageListener | None = None) -> None:
        self.raw_url = raw_url
        self._on_stage = on_stage
        self.normalized_url = normalize_url(raw_url)
        self.domain = extract_domain(self.normalized_url)
        self.is_short_circuited: bool = False
        self.short_circuit_threat: ThreatLevel | None = None
        self.deciding_stage: str = ""
        self.category: str | None = None
        self.scores: dict[str, float] = {}
        self.domain_signals: dict[str, str] = {}
        self.links_not_inspected: bool = False
        self.latency_breakdown: dict[str, float] = {}
        self.dom_text: str = ""
        self.has_password_field: bool = False
        self.screenshot_b64: str | None = None

    def report(self, stage: StageName, status: StageStatus) -> None:
        if self._on_stage is not None:
            self._on_stage(stage, status)

    def short_circuit(self, threat: ThreatLevel, deciding_stage: str, category: str) -> None:
        self.is_short_circuited = True
        self.short_circuit_threat = threat
        self.deciding_stage = deciding_stage
        self.category = category


# --- Cascade ports (implementations live in infrastructure/) ---

class RedisCacheClientProtocol(Protocol):
    async def is_blacklisted(self, url: str) -> bool:
        ...

    async def get_cached_scan(self, sha256_hash: str) -> ScanResponse | None:
        ...

    async def set_cached_scan(self, sha256_hash: str, response: ScanResponse, ttl: int = 3600) -> None:
        ...

    async def get_cached_phash(self, phash: str) -> ScanResponse | None:
        ...

    async def set_cached_phash(self, phash: str, response: ScanResponse, ttl: int = 3600) -> None:
        ...


class DomainEvidenceClient(Protocol):
    async def lookup(self, domain: str) -> DomainEvidence:
        ...


class InspectorClientProtocol(Protocol):
    async def inspect(self, url: str) -> InspectResult:
        ...


class BrandMatchUnavailable(RuntimeError):
    """Visual RAG could not compare the image: the page counts as not verified, never as clean."""


class BrandMatcherClientProtocol(Protocol):
    async def match_brand(
        self, image_b64: str, current_domain: str | None, image_source: ImageSource
    ) -> BrandMatchResult:
        ...


class TriageClient(Protocol):
    async def triage(self, text: str) -> TriageResult | None:
        ...


# --- Cascade stages (Chain of Responsibility) ---

class Stage(Protocol):
    name: StageName

    async def process(self, ctx: StageContext) -> None:
        ...


class Stage0CacheAndFeeds:
    """Stage 0: ultra-fast Redis check (< 5ms) against threat intelligence feeds."""

    name = StageName.STAGE_0_CACHE

    def __init__(self, cache_client: RedisCacheClientProtocol) -> None:
        self._cache = cache_client

    async def process(self, ctx: StageContext) -> None:
        started = time.perf_counter()
        is_hit = await self._cache.is_blacklisted(ctx.normalized_url)
        ctx.latency_breakdown["stage_0"] = elapsed_ms(started)

        if is_hit:
            ctx.short_circuit(ThreatLevel.SCAM, "stage_0_blacklist_feed", "blacklist_feed")
            ctx.scores["is_phishing"] = 1.0


class Stage1ReputationAndSignals:
    """Stage 1: registration age, first certificate, popularity and typosquatting of the domain."""

    name = StageName.STAGE_1_SIGNALS

    def __init__(self, evidence_client: DomainEvidenceClient, protected: list[str] | None = None) -> None:
        self._evidence = evidence_client
        self._protected = protected if protected is not None else protected_domains()

    async def process(self, ctx: StageContext) -> None:
        started = time.perf_counter()
        evidence = await self._evidence.lookup(ctx.domain)
        ctx.latency_breakdown["stage_1"] = elapsed_ms(started)

        imitated = find_imitated_domain(ctx.domain, self._protected)
        assessment = assess_domain(evidence, imitated)
        _record_signals(ctx, evidence, imitated, assessment)

        if assessment.threat is ThreatLevel.SCAM:
            ctx.short_circuit(ThreatLevel.SCAM, "stage_1_young_lookalike", "brand_spoofing")
            ctx.scores["is_phishing"] = 1.0
            return
        if assessment.score_floor is not None:
            raise_score(ctx, assessment.score_floor)
            ctx.deciding_stage = "stage_1_domain_signals"


def _record_signals(ctx: StageContext, evidence: DomainEvidence, imitated: str | None, assessment: DomainAssessment) -> None:
    ctx.domain_signals.update(evidence.as_signals())
    if imitated:
        ctx.domain_signals["imitates"] = imitated
    if assessment.is_reputable:
        ctx.domain_signals["reputation"] = "high"


def raise_score(ctx: StageContext, score: float) -> None:
    """Scores only go up: a later stage cannot clear what an earlier one found suspicious."""
    ctx.scores["is_phishing"] = max(ctx.scores.get("is_phishing", 0.0), score)


class Stage2RemoteInspection:
    """Stage 2: headless Playwright inspection, Visual RAG and semantic triage with ethical fallback."""

    name = StageName.STAGE_2_INSPECTION

    def __init__(
        self,
        inspector_client: InspectorClientProtocol,
        triage_client: TriageClient,
        brand_matcher: BrandMatcherClientProtocol | None = None,
    ) -> None:
        self._inspector = inspector_client
        self._triage = triage_client
        self._brand_matcher = brand_matcher

    async def process(self, ctx: StageContext) -> None:
        started = time.perf_counter()
        result = await self._inspector.inspect(ctx.normalized_url)
        ctx.latency_breakdown["stage_2_inspection"] = elapsed_ms(started)

        # Strict ethical rule: an anti-bot block or network error NEVER returns SEGURO.
        if result.is_blocked:
            ctx.short_circuit(
                ThreatLevel.INCONCLUSIVE, "stage_2_antibot_or_error", result.blocked_reason or "antibot_challenge"
            )
            ctx.links_not_inspected = True
            ctx.scores["is_phishing"] = 0.50
            return

        ctx.dom_text = result.dom_text
        ctx.has_password_field = result.has_password_field
        ctx.screenshot_b64 = result.screenshot_b64

        await self._check_brand_spoofing(ctx)
        if ctx.is_short_circuited:
            return
        await self._triage_page(ctx)

    async def _check_brand_spoofing(self, ctx: StageContext) -> None:
        """Visual RAG: compares the screenshot against the protected brands catalog."""
        if not (self._brand_matcher and ctx.screenshot_b64):
            return

        ctx.report(StageName.VISUAL_RAG, "started")
        started = time.perf_counter()
        try:
            match = await self._brand_matcher.match_brand(ctx.screenshot_b64, ctx.domain, ImageSource.PAGE_SCREENSHOT)
        except BrandMatchUnavailable:
            # Same ethics rule as a link we could not open: at most CUIDADO, never SEGURO.
            ctx.links_not_inspected = True
            return
        finally:
            ctx.latency_breakdown["stage_2_visual_rag"] = elapsed_ms(started)
            ctx.report(StageName.VISUAL_RAG, "done")
        if match.possible_brand:
            ctx.domain_signals["possible_brand"] = match.possible_brand
        if not match.is_spoofing:
            return

        ctx.short_circuit(ThreatLevel.SCAM, "visual_rag_brand_spoofing", "brand_spoofing")
        ctx.scores["is_phishing"] = 1.0
        ctx.scores["brand_spoofing"] = 1.0
        ctx.domain_signals["spoofed_brand"] = match.matched_brand or "Desconhecido"
        ctx.domain_signals["official_domains"] = ", ".join(match.official_domains)

    async def _triage_page(self, ctx: StageContext) -> None:
        started = time.perf_counter()
        triage = await self._triage.triage(ctx.dom_text or ctx.domain)
        ctx.latency_breakdown["stage_2_triage"] = elapsed_ms(started)

        if triage is None:
            ctx.short_circuit(ThreatLevel.INCONCLUSIVE, "stage_2_triage_unavailable", "triage_failure")
            ctx.links_not_inspected = True
            return

        score = triage.is_phishing
        is_trusted = ctx.domain_signals.get("reputation") == "high"
        if ctx.has_password_field and not is_trusted:
            score = max(score, 0.85)

        raise_score(ctx, score)
        ctx.category = triage.persuasion.value
        ctx.deciding_stage = "stage_2_inspection"


class Cascade:
    """Orchestrates the chain of stages for URL inspection."""

    def __init__(self, stages: list[Stage], policy: ThresholdPolicy) -> None:
        self._stages = stages
        self._policy = policy

    def _decide_from_scores(self, ctx: StageContext) -> ThreatLevel:
        # Ethics rule: a URL no stage could score is unknown, never SEGURO.
        if "is_phishing" not in ctx.scores:
            ctx.deciding_stage = ctx.deciding_stage or "no_stage_scored"
            return ThreatLevel.INCONCLUSIVE
        return decide(
            RiskScore(ctx.scores["is_phishing"]), has_unverified_links=ctx.links_not_inspected, policy=self._policy
        )

    async def run(self, ctx: StageContext) -> ScanResponse:
        for stage in self._stages:
            if ctx.is_short_circuited:
                ctx.report(stage.name, "skipped")
                continue
            ctx.report(stage.name, "started")
            await stage.process(ctx)
            ctx.report(stage.name, "done")

        threat = ctx.short_circuit_threat or self._decide_from_scores(ctx)
        persuasion = Persuasion(ctx.category) if ctx.category in Persuasion else None
        return ScanResponse(
            id=uuid4(),
            threat_level=threat,
            verdict_message=verdict_message_for(threat, persuasion, category=ctx.category),
            details=ScanDetails(
                channel=Channel.URL,
                deciding_stage=ctx.deciding_stage,
                category=ctx.category,
                scores=ctx.scores,
                domain_signals=ctx.domain_signals or None,
                links_not_inspected=ctx.links_not_inspected,
                latency_breakdown=ctx.latency_breakdown,
            ),
        )
