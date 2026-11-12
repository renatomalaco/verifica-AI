"""R6 acceptance: one scan produces one trace across orchestrator, ai-gateway and url-inspector."""

import asyncio
import contextvars

import httpx
import pytest
import respx
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind

from ai_gateway.api.main import app as gateway_app, get_jev_client
from ai_gateway.infrastructure.jev_client import FakeJevClient
from observability import (
    build_meter_provider,
    build_tracer_provider,
    instrument_app,
    instrument_httpx,
)
from scan_orchestrator.api.dependencies import get_redis_client, get_settings
from scan_orchestrator.api.main import app as orchestrator_app
from scan_orchestrator.infrastructure.fakes import FakeRedisCacheClient
from scan_orchestrator.settings import Settings
from url_inspector.api.main import app as inspector_app, get_browser_driver
from url_inspector.infrastructure.fakes import FakeBrowserDriver

SCANNED_URL = "https://banco-golpe-exemplo.com.br/login"
SERVICES = {
    "scan-orchestrator": orchestrator_app,
    "ai-gateway": gateway_app,
    "url-inspector": inspector_app,
}


def _forward_to(app: FastAPI):
    """
    Delivers the orchestrator's real HTTP request to an in-process service. It runs in an empty
    context, as a separate process would, so only the traceparent header can link the spans.
    """

    async def call(request: httpx.Request) -> httpx.Response:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://internal"
        ) as client:
            answer = await client.request(
                request.method, request.url.path, content=request.content, headers=request.headers
            )
        return httpx.Response(answer.status_code, content=answer.content, headers=answer.headers)

    async def handler(request: httpx.Request) -> httpx.Response:
        return await asyncio.create_task(call(request), context=contextvars.Context())

    return handler


@pytest.fixture
def traced_services():
    exporter = InMemorySpanExporter()
    providers = {}
    for name, app in SERVICES.items():
        resource = Resource.create({"service.name": name})
        providers[name] = (
            build_tracer_provider(resource, exporter),
            build_meter_provider(resource, InMemoryMetricReader()),
        )
        instrument_app(app, *providers[name])
        app.middleware_stack = None  # an earlier test may have built the stack without telemetry
    instrument_httpx(*providers["scan-orchestrator"])
    orchestrator_app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        AI_GATEWAY_URL="http://ai-gateway:8000",
        URL_INSPECTOR_URL="http://url-inspector:8000",
    )
    orchestrator_app.dependency_overrides[get_redis_client] = FakeRedisCacheClient
    gateway_app.dependency_overrides[get_jev_client] = FakeJevClient
    inspector_app.dependency_overrides[get_browser_driver] = FakeBrowserDriver

    yield exporter, [tracer for tracer, _ in providers.values()]

    HTTPXClientInstrumentor().uninstrument()
    for app in SERVICES.values():
        FastAPIInstrumentor.uninstrument_app(app)
    orchestrator_app.dependency_overrides.pop(get_redis_client, None)
    gateway_app.dependency_overrides.clear()
    inspector_app.dependency_overrides.clear()


async def _scan_a_link() -> httpx.Response:
    with respx.mock:
        respx.route(host="ai-gateway").mock(side_effect=_forward_to(gateway_app))
        respx.route(host="url-inspector").mock(side_effect=_forward_to(inspector_app))
        async with AsyncClient(
            transport=ASGITransport(app=orchestrator_app), base_url="http://test"
        ) as client:
            return await client.post("/api/v1/scans", json={"content": SCANNED_URL})


def _finished_spans(exporter, tracers):
    for tracer in tracers:
        tracer.force_flush()
    return exporter.get_finished_spans()


async def test_one_scan_is_one_trace_across_orchestrator_gateway_and_inspector(traced_services):
    exporter, tracers = traced_services

    response = await _scan_a_link()
    spans = _finished_spans(exporter, tracers)

    assert response.status_code == 200
    assert {span.context.trace_id for span in spans} == {spans[0].context.trace_id}
    assert {span.resource.attributes["service.name"] for span in spans} == set(SERVICES)


async def test_downstream_server_spans_are_children_of_the_orchestrator_calls(traced_services):
    exporter, tracers = traced_services

    await _scan_a_link()
    spans = _finished_spans(exporter, tracers)

    orchestrator_calls = {
        span.context.span_id
        for span in spans
        if span.kind is SpanKind.CLIENT
        and span.resource.attributes["service.name"] == "scan-orchestrator"
    }
    downstream = [
        span
        for span in spans
        if span.kind is SpanKind.SERVER
        and span.resource.attributes["service.name"] != "scan-orchestrator"
    ]
    assert {span.name for span in downstream} == {"POST /v1/triage", "POST /inspect"}
    assert all(span.parent.span_id in orchestrator_calls for span in downstream)


async def test_the_scanned_link_is_in_no_span(traced_services):
    exporter, tracers = traced_services

    await _scan_a_link()
    spans = _finished_spans(exporter, tracers)

    exported = "\n".join(f"{span.name} {dict(span.attributes)}" for span in spans)
    assert "banco-golpe-exemplo" not in exported
