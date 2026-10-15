"""Structured logging.

* stdlib ``logging`` is configured by Django's LOGGING setting (JSON lines on stdout).
* ``loguru`` (used all over the code base) is forwarded into stdlib logging, so one pipeline handles both and the
  OpenTelemetry logging handler (added in config/telemetry.py) also sees every record.
* Every JSON line carries ``trace_id`` / ``span_id`` of the active span, so a log line can be joined to its trace.
"""
import json
import logging
import sys
from datetime import datetime, timezone

from loguru import logger

_RESERVED = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}


def _span_ids() -> tuple[str, str]:
    try:
        from opentelemetry import trace

        ctx = trace.get_current_span().get_span_context()
        if ctx and ctx.is_valid:
            return format(ctx.trace_id, "032x"), format(ctx.span_id, "016x")
    except Exception:  # telemetry must never break logging
        pass
    return "", ""


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        trace_id, span_id = _span_ids()
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "trace_id": trace_id,
            "span_id": span_id,
        }
        for key, value in record.__dict__.items():  # extra={...}
            if key not in _RESERVED and not key.startswith("otel"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def _loguru_to_stdlib(message) -> None:
    rec = message.record
    level = rec["level"].no
    std_logger = logging.getLogger(rec["name"] or "app")
    if not std_logger.isEnabledFor(level):
        return
    exc = rec["exception"]
    exc_info = (exc.type, exc.value, exc.traceback) if exc else None
    record = std_logger.makeRecord(
        std_logger.name, level, rec["file"].path, rec["line"], rec["message"], (), exc_info, func=rec["function"]
    )
    std_logger.handle(record)


def configure_loguru(level: str = "INFO") -> None:
    logger.remove()
    logger.add(_loguru_to_stdlib, level=level, format="{message}", backtrace=False, diagnose=False)


class InterceptHandler(logging.Handler):
    """Kept for backwards compatibility with the original project (stdlib -> loguru). Not installed by default."""

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())
