"""KYC onboarding: photos (local storage fallback) + next of kin + chosen account => the account opens by itself."""
import os

import pytest
from django.conf import settings
from django.core import mail

from core_apps.accounts.models import BankAccount
from tests.conftest import make_user, tiny_png

pytestmark = pytest.mark.django_db

KIN = {
    "title": "mrs", "first_name": "Next", "last_name": "Kin", "date_of_birth": "1980-01-01", "gender": "female",
    "relationship": "Spouse", "email_address": "kin@example.com", "phone_number": "+254700000000",
    "address": "1 Street", "city": "Nairobi", "country": "KE", "is_primary": True,
}


def test_profile_can_be_read_without_cloudinary(as_user, customer):
    r = as_user(customer).get("/api/v1/profiles/my-profile/")
    assert r.status_code == 200
    assert "profile" in r.json() or "email" in r.json()


def test_photos_are_stored_locally_and_urls_are_absolute(as_user, customer):
    api = as_user(customer)
    r = api.patch("/api/v1/profiles/my-profile/", {"photo": tiny_png("p.png"), "id_photo": tiny_png("i.png"), "signature_photo": tiny_png("s.png"), "account_currency": "us_dollar", "account_type": "current"}, format="multipart")
    assert r.status_code == 200, r.content
    profile = customer.profile
    profile.refresh_from_db()
    for field in ("photo", "id_photo", "signature_photo"):
        url = getattr(profile, f"{field}_url")
        assert url.startswith(settings.MEDIA_PUBLIC_URL + settings.MEDIA_URL), url   # URLField needs an absolute URL
    stored = [f for _root, _dirs, files in os.walk(settings.MEDIA_ROOT) for f in files]
    assert len(stored) >= 3


def test_account_opens_automatically_once_everything_is_in_place(as_user, customer):
    api = as_user(customer)
    assert not BankAccount.objects.filter(user=customer).exists()
    # next of kin first: nothing happens yet
    assert api.post("/api/v1/profiles/my-profile/next-of-kin/", KIN, format="json").status_code in (200, 201)
    assert not BankAccount.objects.filter(user=customer).exists()
    # photos + account choice: the (eager) upload task completes the profile and opens the account
    r = api.patch("/api/v1/profiles/my-profile/", {"photo": tiny_png("p.png"), "id_photo": tiny_png("i.png"), "signature_photo": tiny_png("s.png"), "account_currency": "us_dollar", "account_type": "savings"}, format="multipart")
    assert r.status_code == 200, r.content
    accounts = BankAccount.objects.filter(user=customer)
    assert accounts.count() == 1, "exactly one account (no duplicate from the view and the task)"
    account = accounts.get()
    assert account.account_type == "savings" and account.is_primary and account.kyc_verified is False
    assert any("account" in m.subject.lower() for m in mail.outbox)


def test_next_of_kin_added_last_also_opens_the_account(as_user, customer):
    api = as_user(customer)
    api.patch("/api/v1/profiles/my-profile/", {"photo": tiny_png("p.png"), "id_photo": tiny_png("i.png"), "signature_photo": tiny_png("s.png"), "account_currency": "pound_sterling", "account_type": "current"}, format="multipart")
    assert not BankAccount.objects.filter(user=customer).exists()
    api.post("/api/v1/profiles/my-profile/next-of-kin/", KIN, format="json")
    assert BankAccount.objects.filter(user=customer, currency="pound_sterling").count() == 1


def test_profiles_list_is_branch_manager_only(as_user, customer, manager):
    make_user()
    assert as_user(customer).get("/api/v1/profiles/all/").status_code == 403
    assert as_user(manager).get("/api/v1/profiles/all/").status_code == 200
