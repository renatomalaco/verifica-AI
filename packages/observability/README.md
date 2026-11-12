# observability

One `configure_telemetry(service_name, app)` call per service: OpenTelemetry traces and metrics over OTLP,
W3C `traceparent` propagation through FastAPI and httpx, and a privacy filter that keeps only technical
attributes (no pasted text, scanned URL, client IP or exception message ever leaves the process).
Without `OTEL_EXPORTER_OTLP_ENDPOINT` it does nothing.
