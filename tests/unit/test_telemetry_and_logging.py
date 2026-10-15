import json
import logging

import pytest
from django.http import HttpResponse
from django.test import RequestFactory
from opentelemetry.sdk.trace import TracerProvider

from core_apps.common import telemetry as bank_telemetry
from core_apps.common.logging import JsonFormatter
from core_apps.common.middleware import TraceIdHeaderMiddleware


def test_business_metric_helpers_never_raise_without_an_sdk():
    bank_telemetry.login("success")
    bank_telemetry.otp("invalid")
    bank_telemetry.registration()
    bank_telemetry.transaction("transfer", "completed", 12.5, "us_dollar")
    bank_telemetry.transaction("transfer", "failed")
    bank_telemetry.account_opened("us_dollar", "current")
    bank_telemetry.kyc("verified")
    bank_telemetry.card("created")
    bank_telemetry.email("otp", "sent")


def test_span_context_manager_marks_failures_and_reraises():
    with pytest.raises(ValueError):
        with bank_telemetry.span("bank.test", amount=10, note="x"):
            raise ValueError("boom")


def test_json_formatter_includes_trace_ids_when_a_span_is_active():
    tracer = TracerProvider().get_tracer("test")
    with tracer.start_as_current_span("unit") as span:
        record = logging.LogRecord("app", logging.INFO, __file__, 10, "hello %s", ("world",), None)
        payload = json.loads(JsonFormatter().format(record))
        assert payload["message"] == "hello world" and payload["level"] == "INFO"
        assert payload["trace_id"] == format(span.get_span_context().trace_id, "032x")
        assert payload["span_id"] == format(span.get_span_context().span_id, "016x")


def test_json_formatter_without_a_span_has_empty_ids_and_includes_exceptions():
    try:
        raise RuntimeError("bad")
    except RuntimeError:
        import sys
        record = logging.LogRecord("app", logging.ERROR, __file__, 1, "failed", (), sys.exc_info())
    payload = json.loads(JsonFormatter().format(record))
    assert payload["trace_id"] == "" and "RuntimeError" in payload["exception"]


def test_trace_id_header_middleware_exposes_the_trace_id():
    tracer = TracerProvider().get_tracer("test")
    middleware = TraceIdHeaderMiddleware(lambda request: HttpResponse("ok"))
    with tracer.start_as_current_span("request") as span:
        response = middleware(RequestFactory().get("/"))
    assert response["X-Trace-Id"] == format(span.get_span_context().trace_id, "032x")


def test_trace_id_header_absent_without_a_span():
    response = TraceIdHeaderMiddleware(lambda request: HttpResponse("ok"))(RequestFactory().get("/"))
    assert "X-Trace-Id" not in response
