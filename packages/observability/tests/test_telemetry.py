import time

import httpx
import pytest
import respx
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from observability import (
    SAFE_ATTRIBUTES,
    build_meter_provider,
    build_tracer_provider,
    configure_telemetry,
    instrument_app,
    instrument_httpx,
)

PASTED_TEXT = "Seu PIX foi bloqueado, confirme seu CPF agora"
SCANNED_DOMAIN = "banco-golpe-exemplo.com.br"
RESOURCE = Resource.create({"service.name": "test-service"})


def _app() -> FastAPI:
    app = FastAPI()

    @app.post("/scans/{scan_id}")
    async def scan(scan_id: str, body: dict) -> dict:
        async with httpx.AsyncClient() as client:
            await client.get(
                f"https://rdap.org/domain/{SCANNED_DOMAIN}", params={"q": body["content"]}
            )
        return {"ok": True}

    @app.get("/boom")
    async def boom() -> dict:
        raise ValueError(f"could not read {PASTED_TEXT}")

    return app


@pytest.fixture
def telemetry():
    """An instrumented app exporting to memory: tests read what would reach the collector."""
    spans, reader = InMemorySpanExporter(), InMemoryMetricReader()
    tracer_provider = build_tracer_provider(RESOURCE, spans)
    meter_provider = build_meter_provider(RESOURCE, reader)
    app = _app()
    instrument_app(app, tracer_provider, meter_provider)
    instrument_httpx(tracer_provider, meter_provider)
    yield app, tracer_provider, spans, reader
    HTTPXClientInstrumentor().uninstrument()
    FastAPIInstrumentor.uninstrument_app(app)


async def _post_scan(app: FastAPI) -> httpx.Response:
    with respx.mock:
        respx.get(url__startswith="https://rdap.org/").respond(404)
        transport = ASGITransport(app=app, client=("203.0.113.7", 50000))
        async with AsyncClient(transport=transport, base_url="http://orchestrator") as client:
            return await client.post(
                f"/scans/abc?url=https://{SCANNED_DOMAIN}",
                json={"content": PASTED_TEXT},
                headers={"user-agent": "Mozilla/5.0 (Linux; Android 14; Moto G)"},
            )


def _everything_exported(spans) -> str:
    parts = []
    for span in spans:
        parts.append(span.name)
        parts.extend(f"{k}={v}" for k, v in span.attributes.items())
        parts.extend(f"{k}={v}" for event in span.events for k, v in event.attributes.items())
        parts.append(span.status.description or "")
    return "\n".join(parts)


async def test_without_an_otlp_endpoint_telemetry_does_nothing(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    app = _app()

    configure_telemetry("test-service", app)

    assert not getattr(app, "_is_instrumented_by_opentelemetry", False)
    assert isinstance(trace.get_tracer_provider(), trace.ProxyTracerProvider)


async def test_spans_keep_route_method_and_status(telemetry):
    app, tracer_provider, spans, _ = telemetry

    await _post_scan(app)
    tracer_provider.force_flush()

    server = next(s for s in spans.get_finished_spans() if s.kind is trace.SpanKind.SERVER)
    assert server.name == "POST /scans/{scan_id}"
    assert server.attributes["http.route"] == "/scans/{scan_id}"
    assert set(server.attributes) <= SAFE_ATTRIBUTES


async def test_outgoing_calls_name_the_host_they_called_but_not_the_path(telemetry):
    app, tracer_provider, spans, _ = telemetry

    await _post_scan(app)
    tracer_provider.force_flush()

    client = next(s for s in spans.get_finished_spans() if s.kind is trace.SpanKind.CLIENT)
    assert client.attributes["server.address"] == "rdap.org"


async def test_spans_never_carry_content_urls_ip_or_user_agent(telemetry):
    app, tracer_provider, spans, _ = telemetry

    await _post_scan(app)
    tracer_provider.force_flush()

    exported = _everything_exported(spans.get_finished_spans())
    assert len(spans.get_finished_spans()) == 2  # server + outgoing RDAP call
    for leaked in ("PIX", "CPF", SCANNED_DOMAIN, "203.0.113.7", "Android", "/scans/abc"):
        assert leaked not in exported


async def test_exception_messages_never_leave_the_process(telemetry):
    app, tracer_provider, spans, _ = telemetry

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t"
    ) as client:
        await client.get("/boom")
    tracer_provider.force_flush()

    server = next(s for s in spans.get_finished_spans() if s.kind is trace.SpanKind.SERVER)
    assert server.status.status_code is trace.StatusCode.ERROR
    assert [dict(e.attributes) for e in server.events] == [{"exception.type": "ValueError"}]
    assert PASTED_TEXT not in _everything_exported([server])


async def test_metrics_keep_only_technical_labels(telemetry):
    app, _, _, reader = telemetry

    await _post_scan(app)

    points = [
        point
        for resource_metrics in reader.get_metrics_data().resource_metrics
        for scope in resource_metrics.scope_metrics
        for metric in scope.metrics
        for point in metric.data.data_points
    ]
    assert points
    assert all(set(point.attributes) <= SAFE_ATTRIBUTES for point in points)


async def test_a_collector_outage_never_fails_or_slows_a_request():
    unreachable = OTLPSpanExporter(endpoint="http://127.0.0.1:9/v1/traces", timeout=1)
    tracer_provider = build_tracer_provider(RESOURCE, unreachable)
    app = FastAPI()

    @app.get("/ping")
    async def ping() -> dict:
        return {"ok": True}

    instrument_app(app, tracer_provider, build_meter_provider(RESOURCE, InMemoryMetricReader()))
    started = time.perf_counter()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        statuses = [(await client.get("/ping")).status_code for _ in range(50)]
    elapsed = time.perf_counter() - started
    FastAPIInstrumentor.uninstrument_app(app)
    tracer_provider.shutdown()

    assert statuses == [200] * 50
    assert elapsed < 2.0
