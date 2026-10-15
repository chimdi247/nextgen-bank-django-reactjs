"""The full two-step authentication lifecycle through the real HTTP API (DRF test client, real DB, locmem mail)."""
import re

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone
from freezegun import freeze_time

from tests.conftest import PASSWORD, last_otp, make_user

User = get_user_model()
pytestmark = pytest.mark.django_db

REGISTER = {
    "email": "newcustomer@example.com", "first_name": "New", "last_name": "Customer", "id_no": 777001,
    "security_question": "favorite_color", "security_answer": "green", "password": PASSWORD, "re_password": PASSWORD,
}


def test_register_activate_login_two_step_and_me(api):
    # 1. register -> inactive user + activation e-mail
    r = api.post("/api/v1/auth/users/", REGISTER, format="json")
    assert r.status_code == 201, r.content
    user = User.objects.get(email=REGISTER["email"])
    assert user.is_active is False

    # 2. login is refused until the e-mail address is confirmed
    assert api.post("/api/v1/auth/login/", {"email": REGISTER["email"], "password": PASSWORD}, format="json").status_code >= 400

    # 3. follow the activation link from the e-mail
    body = " ".join(m.body for m in mail.outbox if REGISTER["email"] in m.to)
    uid, token = re.search(r"activate/([^/\s\"'<]+)/([^/\s\"'<]+)", body).groups()
    assert api.post("/api/v1/auth/users/activation/", {"uid": uid, "token": token}, format="json").status_code == 204

    # 4. password step -> OTP e-mail
    mail.outbox.clear()
    assert api.post("/api/v1/auth/login/", {"email": REGISTER["email"], "password": PASSWORD}, format="json").status_code == 200
    otp = last_otp(REGISTER["email"])

    # 5. OTP step -> cookies
    r = api.post("/api/v1/auth/verify-otp/", {"email": REGISTER["email"], "otp": otp}, format="json")
    assert r.status_code == 200, r.content
    assert "access" in r.cookies and "refresh" in r.cookies
    assert r.cookies["access"]["httponly"], "the JWT must not be readable from JavaScript"

    # 6. the cookie authenticates /me; role is exposed, the security answer is not
    me = api.get("/api/v1/auth/users/me/")
    assert me.status_code == 200
    data = me.json()
    assert data["email"] == REGISTER["email"] and data["role"] == "customer"
    assert "security_answer" not in data and "password" not in data

    # 7. a code can only be used once
    assert api.post("/api/v1/auth/verify-otp/", {"email": REGISTER["email"], "otp": otp}, format="json").status_code >= 400


def test_registration_validates_input(api):
    bad = dict(REGISTER, re_password="different")
    assert api.post("/api/v1/auth/users/", bad, format="json").status_code == 400
    make_user(email=REGISTER["email"])
    assert api.post("/api/v1/auth/users/", REGISTER, format="json").status_code == 400  # duplicate e-mail


def test_wrong_password_is_rejected_and_repeated_failures_lock_the_account(api, customer):
    for _ in range(3):  # LOGIN_ATTEMPTS = 3 in the test settings
        r = api.post("/api/v1/auth/login/", {"email": customer.email, "password": "wrong"}, format="json")
        assert r.status_code >= 400
    customer.refresh_from_db()
    assert customer.account_status == "locked"
    # even the right password is refused while locked
    assert api.post("/api/v1/auth/login/", {"email": customer.email, "password": PASSWORD}, format="json").status_code >= 400


def test_otp_is_bound_to_the_email_when_given(api):
    """The original looked users up by OTP alone: with two users holding the same code anyone could log in as the other."""
    a, b = make_user(), make_user()
    for u in (a, b):
        u.set_otp("424242")
    r = api.post("/api/v1/auth/verify-otp/", {"email": b.email, "otp": "424242"}, format="json")
    assert r.status_code == 200
    assert api.get("/api/v1/auth/users/me/").json()["email"] == b.email


def test_expired_otp_is_rejected(api, customer):
    with freeze_time("2030-01-01 12:00:00"):
        customer.set_otp("111222")
    with freeze_time("2030-01-01 12:30:00"):
        r = api.post("/api/v1/auth/verify-otp/", {"email": customer.email, "otp": "111222"}, format="json")
    assert r.status_code >= 400


def test_protected_endpoints_require_authentication(api):
    for path in ["/api/v1/accounts/", "/api/v1/accounts/transactions/", "/api/v1/cards/virtual-cards/", "/api/v1/profiles/my-profile/", "/api/v1/auth/users/me/"]:
        assert api.get(path).status_code in (401, 403), path


def test_logout_clears_the_session_cookies(api, customer):
    customer.set_otp("135790")
    api.post("/api/v1/auth/verify-otp/", {"email": customer.email, "otp": "135790"}, format="json")
    r = api.post("/api/v1/auth/logout/")
    assert r.status_code in (200, 204)
    assert not r.cookies["access"].value
