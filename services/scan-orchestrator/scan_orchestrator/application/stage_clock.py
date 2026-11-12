import time

from contracts import StageName, StageStatus
from scan_orchestrator.domain.cascade import StageListener, elapsed_ms


class StageClock:
    """
    Times each stage from its "started" to its "done" report, then forwards the report.
    A text with two links runs the cascade twice in parallel, so each run gets its own fork:
    the same stage of two runs never pairs up, and every run adds to the same durations.
    """

    def __init__(self, forward: StageListener) -> None:
        self._forward = forward
        self._started: dict[StageName, float] = {}
        self.durations: list[tuple[StageName, float]] = []

    def __call__(self, stage: StageName, status: StageStatus) -> None:
        if status == "started":
            self._started[stage] = time.perf_counter()
        elif status == "done" and stage in self._started:
            self.durations.append((stage, elapsed_ms(self._started.pop(stage))))
        self._forward(stage, status)

    def fork(self) -> "StageClock":
        run = StageClock(self._forward)
        run.durations = self.durations
        return run
