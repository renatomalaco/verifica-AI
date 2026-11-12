import os

import httpx
from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor, RequestInfo
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import MetricReader, PeriodicExportingMetricReader
from opentelemetry.sdk.metrics.view import View
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from opentelemetry.trace import Span

from observability.privacy import SAFE_ATTRIBUTES, PrivacySpanProcessor

ENDPOINT_VARIABLE = "OTEL_EXPORTER_OTLP_ENDPOINT"


def build_tracer_provider(resource: Resource, exporter: SpanExporter) -> TracerProvider:
    provider = TracerProvider(resource=resource)
    # The batch exports on a background thread with a bounded queue: a slow or dead collector
    # drops spans, it never blocks or fails a request.
    provider.add_span_processor(PrivacySpanProcessor(BatchSpanProcessor(exporter)))
    return provider


def build_meter_provider(resource: Resource, reader: MetricReader) -> MeterProvider:
    privacy_view = View(instrument_name="*", attribute_keys=set(SAFE_ATTRIBUTES))
    return MeterProvider(resource=resource, metric_readers=[reader], views=[privacy_view])


def instrument_app(
    app: FastAPI, tracer_provider: TracerProvider, meter_provider: MeterProvider
) -> None:
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
        excluded_urls="/health",  # Docker health checks would flood Jaeger
        exclude_spans=["receive", "send"],
    )


def _record_host(span: Span, request: RequestInfo) -> None:
    # Only the host: the full URL may carry the scanned domain (RDAP, crt.sh) and is dropped.
    url = request.url
    span.set_attribute(
        "server.address", url.host if isinstance(url, httpx.URL) else url[1].decode()
    )


async def _record_host_async(span: Span, request: RequestInfo) -> None:
    _record_host(span, request)


def instrument_httpx(tracer_provider: TracerProvider, meter_provider: MeterProvider) -> None:
    """Every httpx call gets a client span and carries the W3C traceparent header."""
    HTTPXClientInstrumentor().instrument(
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
        request_hook=_record_host,
        async_request_hook=_record_host_async,
    )


def configure_telemetry(service_name: str, app: FastAPI | None = None) -> None:
    """
    Exports traces and metrics over OTLP.
    Without OTEL_EXPORTER_OTLP_ENDPOINT (tests, local dev) it does nothing.
    """
    if not os.environ.get(ENDPOINT_VARIABLE):
        return
    resource = Resource.create({"service.name": service_name})
    tracer_provider = build_tracer_provider(resource, OTLPSpanExporter())
    meter_provider = build_meter_provider(
        resource, PeriodicExportingMetricReader(OTLPMetricExporter())
    )
    trace.set_tracer_provider(tracer_provider)
    metrics.set_meter_provider(meter_provider)
    instrument_httpx(tracer_provider, meter_provider)
    if app is not None:
        instrument_app(app, tracer_provider, meter_provider)
