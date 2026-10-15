"""OpenTelemetry bootstrap (traces + metrics + logs over OTLP/HTTP to the collector).

Auto-instrumentation: Django (HTTP server spans + RED metrics), psycopg2 (SQL), Redis, Celery (task spans and context
propagation through RabbitMQ headers), requests. Manual instrumentation lives in core_apps/common/telemetry.py.

Called once per process: gunicorn ``post_fork`` (config/gunicorn.conf.py), Celery ``worker_process_init`` /
``beat_init`` (config/celery_app.py). Fork-safe by design: nothing is created at import time.
Disable completely with OTEL_SDK_DISABLED=true. Endpoint / interval come from the standard OTEL_* variables.
"""
import logging
import os
import socket

_initialised = False


def init_telemetry(service_name: str | None = None, *, instrument_django: bool = False, business_gauges: bool = False) -> None:
    global _initialised
    if _initialised or os.getenv("OTEL_SDK_DISABLED", "false").lower() == "true":
        return
    _initialised = True

    from opentelemetry import metrics, trace
    from opentelemetry._logs import set_logger_provider
    from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.metrics.view import ExplicitBucketHistogramAggregation, View
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    service = service_name or os.getenv("OTEL_SERVICE_NAME", "nextgen-bank")
    resource = Resource.create(
        {
            "service.name": service,
            "service.instance.id": f"{socket.gethostname()}-{os.getpid()}",
            "deployment.environment": os.getenv("DEPLOYMENT_ENVIRONMENT", "local"),
        }
    )

    # ---- traces
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer_provider)

    # ---- metrics (HTTP durations are in seconds: give them second-scale buckets so p95 / SLO queries are meaningful)
    seconds_buckets = [0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10]
    views = [
        View(instrument_name=name, aggregation=ExplicitBucketHistogramAggregation(seconds_buckets))
        for name in ("http.server.request.duration", "http.client.request.duration")
    ]
    interval = int(os.getenv("OTEL_METRIC_EXPORT_INTERVAL", "15000"))
    reader = PeriodicExportingMetricReader(OTLPMetricExporter(), export_interval_millis=interval)
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader], views=views))

    # ---- logs (stdlib root logger -> OTLP -> Loki). Records carry the active trace/span ids.
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
    set_logger_provider(logger_provider)
    logging.getLogger().addHandler(LoggingHandler(level=logging.INFO, logger_provider=logger_provider))

    # ---- auto-instrumentation of libraries
    from opentelemetry.instrumentation.celery import CeleryInstrumentor
    from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor

    Psycopg2Instrumentor().instrument(skip_dep_check=True)
    RedisInstrumentor().instrument()
    CeleryInstrumentor().instrument()
    RequestsInstrumentor().instrument()
    if instrument_django:
        from opentelemetry.instrumentation.django import DjangoInstrumentor

        DjangoInstrumentor().instrument()

    if business_gauges:
        import django

        django.setup()
        from core_apps.common.telemetry import register_business_gauges

        register_business_gauges()

    logging.getLogger(__name__).info("OpenTelemetry initialised for %s", service)
