"""Helpers shared by the browser and live-API tests: Mailpit access (OTP codes, activation links)."""
import os
import re
import time
import uuid

import requests

BASE_URL = os.getenv("BASE_URL", "http://34.171.152.81:8080").rstrip("/")
MAILPIT_URL = os.getenv("MAILPIT_URL", "http://34.171.152.81:8025").rstrip("/")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "password123")
DEMO_PASSWORD = "password123"


def unique_email(prefix="e2e"):
    return f"{prefix}.{uuid.uuid4().hex[:10]}@example.com"


def _search(email: str):
    r = requests.get(f"{MAILPIT_URL}/api/v1/search", params={"query": f"to:{email}", "limit": 20}, timeout=10)
    r.raise_for_status()
    return r.json().get("messages", [])


def wait_for_mail(email: str, subject_contains: str = "", after: float = 0.0, timeout: int = 60) -> dict:
    """Newest message to `email` created after `after` (epoch seconds) whose subject contains the text."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        for m in _search(email):
            created = m.get("Created", "")
            ok_subject = subject_contains.lower() in m.get("Subject", "").lower()
            if ok_subject and (not after or _epoch(created) >= after):
                body = requests.get(f"{MAILPIT_URL}/api/v1/message/{m['ID']}", timeout=10).json()
                return {"subject": m["Subject"], "text": body.get("Text", ""), "html": body.get("HTML", "")}
        time.sleep(1)
    raise AssertionError(f"no e-mail to {email} with subject containing {subject_contains!r} within {timeout}s")


def _epoch(iso: str) -> float:
    from datetime import datetime

    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def wait_for_otp(email: str, after: float, subject_contains: str = "") -> str:
    msg = wait_for_mail(email, subject_contains, after)
    found = re.search(r"(?<!\d)(\d{6})(?!\d)", msg["text"] or msg["html"])
    assert found, f"no 6-digit code in: {msg['text'][:200]}"
    return found.group(1)


def activation_path(email: str, after: float) -> str:
    msg = wait_for_mail(email, "activat", after)
    found = re.search(r"/activate/[^/\s\"'<]+/[^/\s\"'<]+", msg["html"] + msg["text"])
    assert found, "no activation link in the e-mail"
    return found.group(0)
