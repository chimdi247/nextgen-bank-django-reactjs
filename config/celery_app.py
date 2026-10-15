import os

from celery import Celery
from celery.signals import beat_init, worker_process_init
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

app = Celery("nextgen_bank")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@worker_process_init.connect
def _init_worker_telemetry(**_kwargs):
    """Each prefork child gets its own exporters (threads do not survive fork)."""
    from config.telemetry import init_telemetry

    init_telemetry("nextgen-celery-worker")


@beat_init.connect
def _init_beat_telemetry(**_kwargs):
    """Beat is the single process that exports the DB-backed business KPI gauges."""
    from config.telemetry import init_telemetry

    init_telemetry("nextgen-celery-beat", business_gauges=True)
