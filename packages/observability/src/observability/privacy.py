"""
Pasted content is never persisted, and traces are. So spans and metrics keep an allow-list of
technical attributes: anything else (URLs with the scanned domain, query strings, client IP,
user agent, exception messages) is dropped before it reaches the exporter.
"""

from collections.abc import Mapping

from opentelemetry.context import Context
from opentelemetry.sdk.trace import Event, ReadableSpan, Span, SpanProcessor
from opentelemetry.trace import Link, Status

SAFE_ATTRIBUTES = frozenset(
    {
        # HTTP (current and legacy semantic conventions)
        "http.request.method",
        "http.method",
        "http.response.status_code",
        "http.status_code",
        "http.route",
        "url.scheme",
        "http.scheme",
        "network.protocol.version",
        "http.flavor",
        # Host of an outgoing call: internal services or fixed public APIs (RDAP, crt.sh, Gemini).
        "server.address",
        "server.port",
        "error.type",
        "exception.type",
        # Verifica stage latency labels
        "stage",
        "verdict",
        "channel",
    }
)


def keep_safe(attributes: Mapping | None) -> dict:
    return {key: value for key, value in (attributes or {}).items() if key in SAFE_ATTRIBUTES}


def scrubbed(span: ReadableSpan) -> ReadableSpan:
    return ReadableSpan(
        name=span.name,
        context=span.context,
        parent=span.parent,
        resource=span.resource,
        attributes=keep_safe(span.attributes),
        events=[
            Event(event.name, keep_safe(event.attributes), event.timestamp) for event in span.events
        ],
        links=[Link(link.context) for link in span.links],
        kind=span.kind,
        # The description repeats the exception message.
        status=Status(span.status.status_code),
        start_time=span.start_time,
        end_time=span.end_time,
        instrumentation_scope=span.instrumentation_scope,
    )


class PrivacySpanProcessor(SpanProcessor):
    """Hands the delegate a copy of each finished span with only the safe attributes."""

    def __init__(self, delegate: SpanProcessor) -> None:
        self._delegate = delegate

    def on_start(self, span: Span, parent_context: Context | None = None) -> None:
        self._delegate.on_start(span, parent_context)

    def on_end(self, span: ReadableSpan) -> None:
        self._delegate.on_end(scrubbed(span))

    def shutdown(self) -> None:
        self._delegate.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return self._delegate.force_flush(timeout_millis)
