import importlib

import pytest


def test_env_bool_parses_strings_explicitly(monkeypatch):
    from config.settings.base import env_bool

    for raw, expected in [("True", True), ("true", True), ("1", True), ("False", False), ("false", False), ("0", False), ("", False)]:
        monkeypatch.setenv("X_FLAG", raw)
        assert env_bool("X_FLAG") is expected, raw   # DEBUG="False" used to be truthy
    monkeypatch.delenv("X_FLAG")
    assert env_bool("X_FLAG", True) is True


def test_celery_beat_schedule_entries_all_have_a_schedule():
    from django.conf import settings

    assert settings.CELERY_BEAT_SCHEDULE, "no beat schedule configured"
    for name, entry in settings.CELERY_BEAT_SCHEDULE.items():
        assert "task" in entry and "schedule" in entry, f"{name}: celery beat crashes without a schedule"


def test_throttle_rates_are_not_per_day_anymore():
    from django.conf import settings

    rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    assert not any(r.endswith("/day") and int(r.split("/")[0]) <= 1000 for r in rates.values())


def test_gunicorn_config_initialises_telemetry_per_worker():
    import runpy

    ns = runpy.run_path("config/gunicorn.conf.py")
    assert callable(ns["post_fork"]) and ns["workers"] >= 1


def test_telemetry_init_is_a_noop_when_disabled(monkeypatch):
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    import config.telemetry as telemetry

    telemetry._initialised = False
    telemetry.init_telemetry("x")           # must not import / start any exporter
    assert telemetry._initialised is False


@pytest.mark.django_db
def test_health_endpoint(client):
    response = client.get("/api/v1/health/")
    assert response.status_code == 200 and response.json()["status"] == "ok"
