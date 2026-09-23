"""
Structured logging and optional OpenTelemetry tracing.

- LOG_FORMAT=json emits one JSON object per line (CloudWatch Logs Insights /
  Azure Log Analytics parse it natively); LOG_FORMAT=text is for local reading.
- OTEL_ENABLED=true exports traces over OTLP/HTTP to any collector
  (Jaeger locally, AWS Distro for OpenTelemetry or Azure Monitor in the cloud).
"""

import json
import logging
import sys
from contextvars import ContextVar

from legal_rag.config import Settings, get_settings

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

_RESERVED = set(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        payload.update({k: v for k, v in record.__dict__.items() if k not in _RESERVED})
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        extras = {k: v for k, v in record.__dict__.items() if k not in _RESERVED}
        suffix = " " + " ".join(f"{k}={v}" for k, v in extras.items()) if extras else ""
        return f"{record.levelname:<7} {record.name}: {record.getMessage()}{suffix}"


def configure_logging(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if settings.log_format == "json" else TextFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(settings.log_level.upper())
    for noisy in ("httpx", "httpcore", "urllib3", "botocore", "azure"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def configure_tracing(app=None, settings: Settings | None = None) -> bool:
    """Enables OpenTelemetry tracing when OTEL_ENABLED=true. Returns whether it was enabled."""
    settings = settings or get_settings()
    if not settings.otel_enabled:
        return False

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider(resource=Resource.create({"service.name": settings.otel_service_name}))
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{settings.otel_exporter_otlp_endpoint}/v1/traces"))
    )
    trace.set_tracer_provider(provider)

    if app is not None:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app, excluded_urls="health,ready")
    return True


def get_tracer(name: str):
    """Returns an OpenTelemetry tracer (a no-op tracer when tracing is disabled)."""
    try:
        from opentelemetry import trace

        return trace.get_tracer(name)
    except ImportError:  # pragma: no cover - otel extra not installed
        from contextlib import nullcontext

        class _NoopTracer:
            def start_as_current_span(self, *_args, **_kwargs):
                return nullcontext()

        return _NoopTracer()
