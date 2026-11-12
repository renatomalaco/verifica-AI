"""Adapters that run each ablation mode on the real system code, in process."""

from ai_gateway.domain.envelope import guard_for_model
from contracts import Persuasion, ScanResponse, ThreatLevel, TriageResult
from scan_orchestrator.application.analyze_text import AnalyzeTextUseCase
from scan_orchestrator.domain.cascade import (
    Cascade,
    Stage0CacheAndFeeds,
    Stage1ReputationAndSignals,
    StageContext,
)
from scan_orchestrator.domain.decision import ThresholdPolicy
from scan_orchestrator.domain.scan_input import ScanInput
from scan_orchestrator.infrastructure.fakes import FakeDomainEvidenceClient, FakeRedisCacheClient
from scan_orchestrator.infrastructure.scan_repository import InMemoryScanRepository

from research_runner.application.benchmark_service import Outcome
from research_runner.domain.classical_nlp import ClassicalPTBRClassifier
from research_runner.domain.dataset import Sample, Split
from research_runner.infrastructure.llm_providers import ModelCall

POLICY = ThresholdPolicy()
PROVIDER_FAILURE = "provider_failure"
# The model alone is scored as a binary classifier, like Mode 1b (argmax of two classes).
PURE_VLM_SCAM_CUTOFF = 0.5


def train_classifier(samples: list[Sample], splits: dict[str, Split]) -> ClassicalPTBRClassifier:
    train = [s for s in samples if splits[s.id] is Split.TRAIN]
    return ClassicalPTBRClassifier().fit([s.content for s in train], [s.label for s in train])


def build_url_cascade(feed_urls: list[str]) -> Cascade:
    """Stages 0 and 1 only: page inspection stays off until the R2 egress proxy exists."""
    feeds = FakeRedisCacheClient()  # in-memory store holding a dated feed snapshot
    for url in feed_urls:
        feeds.add_to_blacklist(url)
    # Stage 1 runs its typosquatting rule offline; registry, certificate and Tranco lookups
    # answer "unknown".
    stage1 = Stage1ReputationAndSignals(evidence_client=FakeDomainEvidenceClient())
    return Cascade(stages=[Stage0CacheAndFeeds(feeds), stage1], policy=POLICY)


def _scam_probability(response: ScanResponse) -> float:
    fallback = 1.0 if response.threat_level is ThreatLevel.SCAM else 0.5
    return response.details.scores.get("is_phishing", fallback)


class ClassicalNlpEvaluator:
    def __init__(self, classifier: ClassicalPTBRClassifier) -> None:
        self._classifier = classifier

    async def evaluate(self, sample: Sample) -> Outcome:
        label, _ = self._classifier.predict(sample.content)
        return Outcome(
            label, self._classifier.scam_probability(sample.content), "classical_nlp_ptbr"
        )


class HeuristicEvaluator:
    """Mode 1: what a domain-reputation tool sees. Text without a link gives it nothing to judge."""

    def __init__(self, cascade: Cascade) -> None:
        self._cascade = cascade

    @classmethod
    def with_feed(cls, feed_urls: list[str]) -> "HeuristicEvaluator":
        return cls(build_url_cascade(feed_urls))

    async def evaluate(self, sample: Sample) -> Outcome:
        urls = ScanInput(content=sample.content).extract_urls()
        if not urls:
            return Outcome("SEGURO", 0.5, "no_url_no_signal")
        verdicts = [await self._cascade.run(StageContext(raw_url=url)) for url in urls]
        worst = max(verdicts, key=_scam_probability)
        return Outcome(
            worst.threat_level.value, _scam_probability(worst), worst.details.deciding_stage
        )


class PureVlmEvaluator:
    """Mode 2: the multimodal model alone, behind the gateway's masking and envelope
    (never raw content)."""

    def __init__(self, call: ModelCall) -> None:
        self._call = call

    async def evaluate(self, sample: Sample) -> Outcome:
        try:
            answer, cost = await self._call(guard_for_model(sample.content))
        except RuntimeError:
            # Timeouts, rate limits and malformed answers are failures, never a SEGURO.
            return Outcome(ThreatLevel.INCONCLUSIVE.value, 0.5, PROVIDER_FAILURE)
        predicted = (
            ThreatLevel.SCAM if answer.is_phishing >= PURE_VLM_SCAM_CUTOFF else ThreatLevel.SAFE
        )
        return Outcome(predicted.value, answer.is_phishing, "pure_vlm", cost_usd=cost)


class GatewayTriageClient:
    """ai-gateway's /v1/triage path in process (masking, envelope, model), adding up what
    the calls cost."""

    def __init__(self, call: ModelCall) -> None:
        self._call = call
        self.spent_usd = 0.0

    async def triage(self, text: str) -> TriageResult | None:
        try:
            answer, cost = await self._call(guard_for_model(text))
        except RuntimeError:
            # Same as HttpTriageClient on a gateway error: the cascade falls back to INCONCLUSIVO.
            return None
        self.spent_usd += cost
        return answer


class LocalTriageClient:
    """Stands in for the LLM triage with the local classifier (declared in the report)."""

    def __init__(self, classifier: ClassicalPTBRClassifier) -> None:
        self._classifier = classifier
        self.spent_usd = 0.0  # a local model costs nothing

    async def triage(self, text: str) -> TriageResult:
        return TriageResult(
            is_phishing=self._classifier.scam_probability(text), persuasion=Persuasion.NONE
        )


class CascadeEvaluator:
    """Mode 3: the orchestrator's AnalyzeTextUseCase, exactly as the API runs it."""

    def __init__(
        self, use_case: AnalyzeTextUseCase, triage: GatewayTriageClient | LocalTriageClient
    ) -> None:
        self._use_case = use_case
        self._triage = triage

    @classmethod
    def build(
        cls, triage: GatewayTriageClient | LocalTriageClient, feed_urls: list[str]
    ) -> "CascadeEvaluator":
        use_case = AnalyzeTextUseCase(
            triage_client=triage,
            repository=InMemoryScanRepository(),
            policy=POLICY,
            cascade=build_url_cascade(feed_urls),
        )
        return cls(use_case, triage)

    async def evaluate(self, sample: Sample) -> Outcome:
        spent_before = self._triage.spent_usd
        events = [
            event async for event in self._use_case.execute(ScanInput(content=sample.content))
        ]
        verdict = next(e for e in reversed(events) if isinstance(e, ScanResponse))
        return Outcome(
            verdict.threat_level.value,
            _scam_probability(verdict),
            verdict.details.deciding_stage,
            cost_usd=self._triage.spent_usd - spent_before,
        )
