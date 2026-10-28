"""Adapters that run each ablation mode on the real system code, in process."""

from contracts import Persuasion, ScanResponse, ThreatLevel, TriageResult
from scan_orchestrator.application.analyze_text import AnalyzeTextUseCase
from scan_orchestrator.domain.cascade import Cascade, Stage0CacheAndFeeds, Stage1ReputationAndSignals, StageContext
from scan_orchestrator.domain.decision import ThresholdPolicy
from scan_orchestrator.domain.scan_input import ScanInput
from scan_orchestrator.infrastructure.fakes import FakeRedisCacheClient
from scan_orchestrator.infrastructure.reputation_client import DomainSignalsClient
from scan_orchestrator.infrastructure.scan_repository import InMemoryScanRepository

from research_runner.application.benchmark_service import Outcome
from research_runner.domain.classical_nlp import ClassicalPTBRClassifier
from research_runner.domain.dataset import Sample, Split

POLICY = ThresholdPolicy()


def train_classifier(samples: list[Sample], splits: dict[str, Split]) -> ClassicalPTBRClassifier:
    train = [s for s in samples if splits[s.id] is Split.TRAIN]
    return ClassicalPTBRClassifier().fit([s.content for s in train], [s.label for s in train])


def build_url_cascade(feed_urls: list[str]) -> Cascade:
    """Stages 0 and 1 only: page inspection stays off until the R2 egress proxy exists."""
    feeds = FakeRedisCacheClient()  # in-memory store holding a dated feed snapshot
    for url in feed_urls:
        feeds.add_to_blacklist(url)
    return Cascade(stages=[Stage0CacheAndFeeds(feeds), Stage1ReputationAndSignals(DomainSignalsClient())], policy=POLICY)


def _scam_probability(response: ScanResponse) -> float:
    fallback = 1.0 if response.threat_level is ThreatLevel.SCAM else 0.5
    return response.details.scores.get("is_phishing", fallback)


class ClassicalNlpEvaluator:
    def __init__(self, classifier: ClassicalPTBRClassifier) -> None:
        self._classifier = classifier

    async def evaluate(self, sample: Sample) -> Outcome:
        label, _ = self._classifier.predict(sample.content)
        return Outcome(label, self._classifier.scam_probability(sample.content), "classical_nlp_ptbr")


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
        return Outcome(worst.threat_level.value, _scam_probability(worst), worst.details.deciding_stage)


class LocalTriageClient:
    """Stands in for the LLM triage with the local classifier (declared in the report)."""

    def __init__(self, classifier: ClassicalPTBRClassifier) -> None:
        self._classifier = classifier

    async def triage(self, text: str) -> TriageResult:
        return TriageResult(is_phishing=self._classifier.scam_probability(text), persuasion=Persuasion.NONE)


class CascadeEvaluator:
    """Mode 3: the orchestrator's AnalyzeTextUseCase, exactly as the API runs it."""

    def __init__(self, use_case: AnalyzeTextUseCase) -> None:
        self._use_case = use_case

    @classmethod
    def build(cls, classifier: ClassicalPTBRClassifier, feed_urls: list[str]) -> "CascadeEvaluator":
        use_case = AnalyzeTextUseCase(
            triage_client=LocalTriageClient(classifier),
            repository=InMemoryScanRepository(),
            policy=POLICY,
            cascade=build_url_cascade(feed_urls),
        )
        return cls(use_case)

    async def evaluate(self, sample: Sample) -> Outcome:
        events = [event async for event in self._use_case.execute(ScanInput(content=sample.content))]
        verdict = next(e for e in reversed(events) if isinstance(e, ScanResponse))
        return Outcome(verdict.threat_level.value, _scam_probability(verdict), verdict.details.deciding_stage)
