import os
import re
import secrets
import time
from typing import Callable, Dict, List, Optional, Tuple
import numpy as np
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

TRACEPARENT_REGEX = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


def generate_traceparent(trace_id: Optional[str] = None, flags: str = "01") -> str:
    tid = trace_id or secrets.token_hex(16)
    parent_id = secrets.token_hex(8)
    return f"00-{tid}-{parent_id}-{flags}"


def parse_traceparent(header_val: str) -> Dict[str, str]:
    match = TRACEPARENT_REGEX.match(header_val.strip())
    if not match:
        # Fallback if the header is invalid
        return {
            "version": "00",
            "trace_id": secrets.token_hex(16),
            "parent_id": secrets.token_hex(8),
            "flags": "01",
        }
    return {
        "version": "00",
        "trace_id": match.group(1),
        "parent_id": match.group(2),
        "flags": match.group(3),
    }


class LatencyTracker:
    """In-memory latency distribution tracker for computing P50, P95 and P99."""

    def __init__(self):
        self._records: Dict[str, List[float]] = {}

    def record(self, endpoint: str, latency_ms: float) -> None:
        if endpoint not in self._records:
            self._records[endpoint] = []
        self._records[endpoint].append(latency_ms)

    def get_percentiles(self, endpoint: str) -> Tuple[float, float, float]:
        records = self._records.get(endpoint, [])
        if not records:
            return 0.0, 0.0, 0.0
        arr = np.array(records)
        p50 = float(np.percentile(arr, 50))
        p95 = float(np.percentile(arr, 95))
        p99 = float(np.percentile(arr, 99))
        return p50, p95, p99

    def generate_prometheus_metrics(self) -> str:
        lines = [
            "# HELP http_request_duration_ms Latencia de requisicoes HTTP em milissegundos",
            "# TYPE http_request_duration_ms summary",
        ]
        for ep, records in self._records.items():
            if not records:
                continue
            p50, p95, p99 = self.get_percentiles(ep)
            count = len(records)
            lines.append(f'http_request_duration_ms{{endpoint="{ep}",quantile="0.5"}} {p50:.2f}')
            lines.append(f'http_request_duration_ms{{endpoint="{ep}",quantile="0.95"}} {p95:.2f}')
            lines.append(f'http_request_duration_ms{{endpoint="{ep}",quantile="0.99"}} {p99:.2f}')
            lines.append(f'http_request_duration_ms_count{{endpoint="{ep}"}} {count}')
        return "\n".join(lines) + "\n"


class TraceContextMiddleware(BaseHTTPMiddleware):
    """ASGI middleware for W3C traceparent context propagation and latency measurement."""

    def __init__(self, app, tracker: Optional[LatencyTracker] = None):
        super().__init__(app)
        self.tracker = tracker or LatencyTracker()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        in_tp = request.headers.get("traceparent")
        if in_tp:
            parsed = parse_traceparent(in_tp)
            trace_id = parsed["trace_id"]
            # Generate a new span_id while preserving the request trace_id
            out_tp = generate_traceparent(trace_id=trace_id)
        else:
            trace_id = secrets.token_hex(16)
            out_tp = generate_traceparent(trace_id=trace_id)

        request.state.trace_id = trace_id
        request.state.traceparent = out_tp

        start_time = time.perf_counter()
        response: Response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # Inject traceparent into the HTTP response
        response.headers["traceparent"] = out_tp

        endpoint = request.url.path
        self.tracker.record(endpoint, elapsed_ms)

        return response
