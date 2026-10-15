import re
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from freezegun import freeze_time

from core_apps.user_auth.managers import generate_username
from core_apps.user_auth.utils import generate_otp
from tests.conftest import make_user

User = get_user_model()
pytestmark = pytest.mark.django_db


def test_username_is_generated_from_bank_name_and_fits_the_column():
    for _ in range(50):
        username = generate_username()
        assert re.fullmatch(r"NB-[A-Z0-9]{9}", username)
        assert len(username) == 12  # the column is varchar(12)


def test_create_user_hashes_password_and_normalises_email():
    user = User.objects.create_user(email="Mixed.Case@EXAMPLE.com", password="pw-123456", first_name="A", last_name="B", id_no=111)
    assert user.email == "Mixed.Case@example.com"      # only the domain part is normalised by Django
    assert user.password != "pw-123456" and user.check_password("pw-123456")
    assert user.role == "customer" and user.account_status == "active"


@pytest.mark.parametrize("email,password,msg", [("", "pw", "email"), ("a@b.com", "", "password")])
def test_create_user_requires_email_and_password(email, password, msg):
    with pytest.raises(ValueError, match=msg):
        User.objects.create_user(email=email, password=password, first_name="A", last_name="B", id_no=1)


def test_profile_is_created_by_signal():
    user = make_user()
    assert user.profile.pk is not None


def test_otp_is_six_digits():
    for _ in range(100):
        assert re.fullmatch(r"\d{6}", generate_otp())


def test_otp_valid_once_then_cleared():
    user = make_user()
    user.set_otp("123456")
    assert user.verify_otp("123456") is True
    user.refresh_from_db()
    assert user.otp == "" and user.otp_expiry_time is None
    # a code can only be used once
    user.otp_expiry_time = None
    assert user.otp == ""


def test_wrong_otp_is_rejected():
    user = make_user()
    user.set_otp("123456")
    assert user.verify_otp("654321") is False


def test_otp_expires():
    user = make_user()
    with freeze_time("2030-01-01 12:00:00"):
        user.set_otp("123456")
    with freeze_time("2030-01-01 12:06:00"):  # OTP_EXPIRATION is 5 minutes in test settings
        assert user.verify_otp("123456") is False


def test_account_locks_after_configured_failed_attempts_and_sends_mail():
    user = make_user()
    for _ in range(3):  # LOGIN_ATTEMPTS = 3 in config.settings.test
        user.handle_failed_login_attempts()
    user.refresh_from_db()
    assert user.account_status == "locked" and user.is_locked_out
    assert any("lock" in m.subject.lower() for m in mail.outbox)


def test_lockout_expires_after_lockout_duration():
    user = make_user()
    with freeze_time("2030-01-01 12:00:00"):
        for _ in range(3):
            user.handle_failed_login_attempts()
        assert user.is_locked_out
    with freeze_time("2030-01-01 12:00:00") as frozen:
        frozen.tick(timedelta(minutes=2))
        assert user.is_locked_out is False
    user.refresh_from_db()
    assert user.account_status == "active" and user.failed_login_attempts == 0


def test_reset_failed_attempts():
    user = make_user()
    user.handle_failed_login_attempts()
    user.reset_failed_login_attempts()
    user.refresh_from_db()
    assert user.failed_login_attempts == 0


def test_full_name_and_roles():
    user = make_user("teller", first_name="Ada", last_name="Lovelace")
    assert "Ada" in user.full_name and "Lovelace" in user.full_name
    assert user.has_role("teller") and not user.has_role("customer")
