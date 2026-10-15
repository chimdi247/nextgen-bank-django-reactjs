"""gunicorn settings (used by docker/local/django/start.sh). Telemetry is initialised in each worker AFTER fork,
before the Django app is imported, so the Django instrumentation can patch the middleware stack."""
import os

bind = "0.0.0.0:8000"
workers = int(os.getenv("GUNICORN_WORKERS", "3"))
threads = int(os.getenv("GUNICORN_THREADS", "2"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "60"))
graceful_timeout = 20
max_requests = 2000          # recycle workers: bounds any slow memory growth
max_requests_jitter = 200
accesslog = None             # request logs come from the OTel/JSON logging pipeline and nginx
errorlog = "-"
reload = os.getenv("GUNICORN_RELOAD", "false").lower() == "true"


def post_fork(server, worker):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    from config.telemetry import init_telemetry

    init_telemetry(os.getenv("OTEL_SERVICE_NAME", "nextgen-api"), instrument_django=True)
