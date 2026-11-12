import asyncio

from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.resources import Resource

from contracts import InspectResult, ScanResponse
from observability import build_meter_provider
from scan_orchestrator.application.analyze_text import AnalyzeTextUseCase
from scan_orchestrator.domain.cascade import (
    Cascade,
    Stage0CacheAndFeeds,
    Stage1ReputationAndSignals,
    Stage2RemoteInspection,
)
from scan_orchestrator.domain.decision import ThresholdPolicy
from scan_orchestrator.domain.domain_risk import DomainEvidence
from scan_orchestrator.domain.scan_input import ScanInput
from scan_orchestrator.infrastructure.fakes import FakeRedisCacheClient, FakeTriageClient
from scan_orchestrator.infrastructure.scan_metrics import ScanMetrics
from scan_orchestrator.infrastructure.scan_repository import InMemoryScanRepository

POLICY = ThresholdPolicy(scam=0.90, safe=0.10)
CASCADE_STAGES = {"stage_0_cache", "stage_1_signals", "stage_2_inspection"}


class DelayedEvidence:
    def __init__(self, delays: dict[str, float]) -> None:
        self._delays = delays

    async def lookup(self, domain: str) -> DomainEvidence:
        await asyncio.sleep(self._delays.get(domain, 0.0))
        return DomainEvidence()


class DelayedInspector:
    def __init__(self, delays: dict[str, float]) -> None:
        self._delays = delays

    async def inspect(self, url: str) -> InspectResult:
        await asyncio.sleep(next((d for host, d in self._delays.items() if host in url), 0.0))
        return InspectResult(dom_text="", final_url=url, is_blocked=False)


def _use_case(reader: InMemoryMetricReader, evidence=None, inspector=None) -> AnalyzeTextUseCase:
    cascade = Cascade(
        stages=[
            Stage0CacheAndFeeds(cache_client=FakeRedisCacheClient()),
            Stage1ReputationAndSignals(evidence_client=evidence or DelayedEvidence({})),
            Stage2RemoteInspection(
                inspector_client=inspector or DelayedInspector({}), triage_client=FakeTriageClient()
            ),
        ],
        policy=POLICY,
    )
    meter = build_meter_provider(Resource.create({}), reader).get_meter("test")
    return AnalyzeTextUseCase(
        triage_client=FakeTriageClient(),
        repository=InMemoryScanRepository(),
        policy=POLICY,
        cascade=cascade,
        metrics=ScanMetrics(meter),
    )


async def _scan(use_case: AnalyzeTextUseCase, content: str) -> ScanResponse:
    items = [item async for item in use_case.execute(ScanInput(content=content))]
    return items[-1]


def _histogram(reader: InMemoryMetricReader, name: str) -> list:
    return [
        point
        for resource_metrics in reader.get_metrics_data().resource_metrics
        for scope in resource_metrics.scope_metrics
        for metric in scope.metrics
        if metric.name == name
        for point in metric.data.data_points
    ]


async def test_each_cascade_stage_latency_is_labelled_by_stage_and_verdict():
    reader = InMemoryMetricReader()

    response = await _scan(_use_case(reader), "https://loja-legitima.com.br")

    points = _histogram(reader, "verifica.stage.duration")
    assert {dict(p.attributes)["stage"] for p in points} == CASCADE_STAGES
    assert all(
        dict(p.attributes)
        == {"stage": p.attributes["stage"], "verdict": response.threat_level.value}
        for p in points
    )


async def test_the_whole_scan_latency_is_labelled_by_verdict_and_channel():
    reader = InMemoryMetricReader()

    response = await _scan(_use_case(reader), "Oi, tudo bem? Seu pacote chegou.")

    [point] = _histogram(reader, "verifica.scan.duration")
    assert dict(point.attributes) == {"verdict": response.threat_level.value, "channel": "texto"}
    assert point.count == 1


async def test_parallel_links_keep_their_own_stage_timings():
    # Link A is slow in stage 1 and fast in stage 2; link B the opposite. Pairing "done" with the
    # oldest "started" of the same stage would swap their stage 2 timings.
    reader = InMemoryMetricReader()
    use_case = _use_case(
        reader,
        evidence=DelayedEvidence({"link-a.com.br": 0.2}),
        inspector=DelayedInspector({"link-b.com.br": 0.3}),
    )

    await _scan(use_case, "Veja https://link-a.com.br e https://link-b.com.br")

    [inspection] = [
        p
        for p in _histogram(reader, "verifica.stage.duration")
        if p.attributes["stage"] == "stage_2_inspection"
    ]
    assert inspection.count == 2
    assert inspection.min < 50
    assert inspection.max >= 290
