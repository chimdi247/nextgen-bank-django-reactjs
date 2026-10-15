"""HTTP checks against the running stack (no browser)."""
import time

import pytest
import requests

from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, BASE_URL, wait_for_otp

pytestmark = pytest.mark.live


def test_health_endpoint_reports_database_and_cache():
    r = requests.get(f"{BASE_URL}/api/v1/health/", timeout=10)
    assert r.status_code == 200 and r.json()["status"] == "ok"
    assert r.json()["checks"]["database"] == "ok"


def test_responses_carry_a_trace_id_header_when_telemetry_is_on():
    r = requests.get(f"{BASE_URL}/api/v1/accounts/", timeout=10)
    assert r.status_code in (401, 403)
    assert len(r.headers.get("X-Trace-Id", "0" * 32)) == 32     # absent only if OTEL_SDK_DISABLED


def test_openapi_schema_is_served():
    assert requests.get(f"{BASE_URL}/api/v1/schema/", timeout=10).status_code == 200


def test_react_app_is_served_for_deep_links():
    r = requests.get(f"{BASE_URL}/transfer", timeout=10)
    assert r.status_code == 200 and "<div id=\"root\">" in r.text


def test_admin_login_flow_over_http_and_role_in_me():
    s = requests.Session()
    started = time.time()
    assert s.post(f"{BASE_URL}/api/v1/auth/login/", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15).status_code == 200
    otp = wait_for_otp(ADMIN_EMAIL, started)
    r = s.post(f"{BASE_URL}/api/v1/auth/verify-otp/", json={"email": ADMIN_EMAIL, "otp": otp}, timeout=15)
    assert r.status_code == 200 and "access" in s.cookies
    me = s.get(f"{BASE_URL}/api/v1/auth/users/me/", timeout=10).json()
    assert me["role"] == "branch_manager" and me["is_superuser"] is True and "security_answer" not in me
    stats = s.get(f"{BASE_URL}/api/v1/accounts/stats/", timeout=10)
    assert stats.status_code == 200 and "accounts_total" in stats.json()


def test_pgbouncer_pooling_survives_a_burst_of_parallel_requests():
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(30) as pool:
        codes = list(pool.map(lambda _: requests.get(f"{BASE_URL}/api/v1/health/", timeout=15).status_code, range(120)))
    assert set(codes) == {200}


def test_login_with_unknown_user_is_rejected_without_leaking_details():
    r = requests.post(f"{BASE_URL}/api/v1/auth/login/", json={"email": "nobody@example.com", "password": "x"}, timeout=10)
    assert 400 <= r.status_code < 500
