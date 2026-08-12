"""OpenTelemetry tracing setup."""

import logging
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from app.config import get_settings

logger = logging.getLogger(__name__)
_tracer: trace.Tracer | None = None


def setup_tracing() -> trace.Tracer:
    """Configure OpenTelemetry tracer provider."""
    global _tracer
    settings = get_settings()
    resource = Resource.create({"service.name": settings.otel_service_name})
    provider = TracerProvider(resource=resource)

    if settings.otel_exporter_otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        except ImportError:
            logger.warning("OTLP exporter not available; using console exporter")
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    else:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(__name__)
    return _tracer


def get_tracer() -> trace.Tracer:
    """Return configured tracer."""
    global _tracer
    if _tracer is None:
        return setup_tracing()
    return _tracer


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None):
    """Context manager for tracing a span."""
    tracer = get_tracer()
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))
        yield span
