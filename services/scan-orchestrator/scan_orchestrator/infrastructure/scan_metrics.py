from opentelemetry import metrics
from opentelemetry.metrics import Meter

from contracts import ScanResponse, StageName

# Stage 2 waits up to 12 s for the headless browser, past the SDK default top bucket of 10 s.
LATENCY_BUCKETS_MS = (5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 15000, 30000)


class ScanMetrics:
    """Stage and scan latency histograms (P50/P95/P99 in Grafana), labelled only by stage,
    verdict and channel."""

    def __init__(self, meter: Meter | None = None) -> None:
        meter = meter or metrics.get_meter("scan_orchestrator")
        self._stage = meter.create_histogram(
            "verifica.stage.duration",
            unit="ms",
            description="Latency of each cascade stage",
            explicit_bucket_boundaries_advisory=LATENCY_BUCKETS_MS,
        )
        self._scan = meter.create_histogram(
            "verifica.scan.duration",
            unit="ms",
            description="Latency of a whole scan",
            explicit_bucket_boundaries_advisory=LATENCY_BUCKETS_MS,
        )

    def record(
        self,
        response: ScanResponse,
        stage_durations: list[tuple[StageName, float]],
        total_ms: float,
    ) -> None:
        verdict = response.threat_level.value
        for stage, duration_ms in stage_durations:
            self._stage.record(duration_ms, {"stage": stage.value, "verdict": verdict})
        self._scan.record(total_ms, {"verdict": verdict, "channel": response.details.channel.value})
