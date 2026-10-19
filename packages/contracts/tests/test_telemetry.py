import pytest
from contracts.telemetry import (
    generate_traceparent,
    parse_traceparent,
    LatencyTracker,
    TraceContextMiddleware,
)
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport


def test_generate_and_parse_traceparent():
    tp = generate_traceparent()
    parts = tp.split("-")
    assert len(parts) == 4
    assert parts[0] == "00"  # version
    assert len(parts[1]) == 32  # trace_id (16 bytes hex)
    assert len(parts[2]) == 16  # span_id (8 bytes hex)
    assert parts[3] in ["00", "01"]  # trace_flags

    parsed = parse_traceparent(tp)
    assert parsed["trace_id"] == parts[1]
    assert parsed["parent_id"] == parts[2]


def test_latency_tracker_percentiles():
    tracker = LatencyTracker()
    for val in [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]:
        tracker.record("scan_endpoint", val)

    p50, p95, p99 = tracker.get_percentiles("scan_endpoint")
    assert p50 <= p95 <= p99
    assert p50 == pytest.approx(55.0, rel=1e-1)


@pytest.mark.asyncio
async def test_trace_middleware_propagates_header():
    app = FastAPI()
    tracker = LatencyTracker()
    app.add_middleware(TraceContextMiddleware, tracker=tracker)

    @app.get("/test-endpoint")
    async def sample():
        return {"ok": True}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Without incoming header -> auto-generates traceparent in response
        res = await client.get("/test-endpoint")
        assert res.status_code == 200
        assert "traceparent" in res.headers
        out_tp = res.headers["traceparent"]
        assert len(out_tp.split("-")) == 4

        # With incoming header -> preserves trace_id
        in_tp = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        res2 = await client.get("/test-endpoint", headers={"traceparent": in_tp})
        assert res2.status_code == 200
        assert "traceparent" in res2.headers
        assert "4bf92f3577b34da6a3ce929d0e0e4736" in res2.headers["traceparent"]
