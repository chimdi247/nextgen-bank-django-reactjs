"""Shared fixtures for unit + integration tests."""
import io
import re
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from rest_framework.test import APIClient

from core_apps.accounts.models import BankAccount

User = get_user_model()
PASSWORD = "Str0ng#Passw0rd"
_counter = {"n": 0}


def _next() -> int:
    _counter["n"] += 1
    return _counter["n"]


def make_user(role="customer", **extra):
    n = _next()
    user = User.objects.create_user(
        email=extra.pop("email", f"user{n}@example.com"),
        password=extra.pop("password", PASSWORD),
        first_name=extra.pop("first_name", f"First{n}"),
        last_name=extra.pop("last_name", f"Last{n}"),
        id_no=extra.pop("id_no", 5_000_000 + n),
        security_question="favorite_color",
        security_answer="blue",
        **extra,
    )
    user.is_active = True
    user.role = role
    user.save()
    return user


def make_account(user, balance="1000.00", currency="us_dollar", account_type="current", active=True):
    from core_apps.accounts.utils import generate_account_number

    return BankAccount.objects.create(
        user=user,
        account_number=generate_account_number(currency),
        currency=currency,
        account_type=account_type,
        account_balance=Decimal(balance),
        account_status="active" if active else "inactive",
        is_primary=not BankAccount.objects.filter(user=user).exists(),
        kyc_submitted=active,
        kyc_verified=active,
        fully_activated=active,
    )


def last_otp(to: str | None = None) -> str:
    """The 6-digit code from the newest e-mail in the in-memory outbox."""
    for message in reversed(mail.outbox):
        if to and to not in message.to:
            continue
        found = re.search(r"(?<!\d)(\d{6})(?!\d)", message.body)
        if found:
            return found.group(1)
    raise AssertionError("no OTP e-mail found")


def tiny_png(name="x.png"):
    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (200, 242, 58)).save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def customer(db):
    return make_user("customer")


@pytest.fixture
def other_customer(db):
    return make_user("customer")


@pytest.fixture
def teller(db):
    return make_user("teller")


@pytest.fixture
def executive(db):
    return make_user("account_executive")


@pytest.fixture
def manager(db):
    return make_user("branch_manager")


@pytest.fixture
def as_user(api):
    def _login(user):
        api.force_authenticate(user=user)
        return api

    return _login


@pytest.fixture(autouse=True)
def _clear_mail_and_cache():
    from django.core.cache import cache

    mail.outbox.clear()
    cache.clear()
    yield
