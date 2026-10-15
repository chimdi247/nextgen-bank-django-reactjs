"""Creates verified, funded demo / load-test customers (and removes them again).

    python manage.py seed_demo_data --customers 20 --prefix perf --balance 100000
    python manage.py seed_demo_data --prefix perf --cleanup

Users are perf1@example.com ... with password ``Perf#12345``; every one gets a complete profile, a next of kin, and a
KYC-verified USD current account, so they can log in and move money straight away (tests/k6 and tests/selenium rely
on this). Passwords go through Django's hasher (Argon2), exactly like a real registration.
"""
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core_apps.accounts.models import BankAccount
from core_apps.accounts.utils import generate_account_number
from core_apps.user_profile.models import NextOfKin

User = get_user_model()
PASSWORD = "Perf#12345"


class Command(BaseCommand):
    help = "Seed (or remove) verified, funded customers for demos and load tests"

    def add_arguments(self, parser):
        parser.add_argument("--customers", type=int, default=10)
        parser.add_argument("--prefix", default="perf")
        parser.add_argument("--domain", default="example.com")
        parser.add_argument("--balance", type=Decimal, default=Decimal("100000.00"))
        parser.add_argument("--cleanup", action="store_true")

    def handle(self, *args, **opts):
        prefix, domain = opts["prefix"], opts["domain"]
        if opts["cleanup"]:
            deleted, _ = User.objects.filter(email__startswith=prefix, email__endswith=f"@{domain}").delete()
            self.stdout.write(self.style.SUCCESS(f"removed {deleted} rows for {prefix}*@{domain}"))
            return

        created = 0
        for n in range(1, opts["customers"] + 1):
            email = f"{prefix}{n}@{domain}"
            if User.objects.filter(email=email).exists():
                continue
            with transaction.atomic():
                user = User.objects.create_user(
                    email=email,
                    password=PASSWORD,
                    first_name=f"{prefix.title()}{n}",
                    last_name="Customer",
                    id_no=900_000_000 + n + (sum(map(ord, prefix)) % 1000) * 10_000,
                    security_question="favorite_color",
                    security_answer="blue",
                )
                user.is_active = True
                user.save()
                profile = user.profile  # created by the post_save signal
                profile.account_currency = BankAccount.AccountCurrency.DOLLAR
                profile.account_type = BankAccount.AccountType.CURRENT
                profile.photo, profile.id_photo, profile.signature_photo = "seed/photo", "seed/id", "seed/signature"
                placeholder = f"{settings.MEDIA_PUBLIC_URL}/media/seed/placeholder.svg"
                profile.photo_url = profile.id_photo_url = profile.signature_photo_url = placeholder
                profile.save()
                NextOfKin.objects.create(
                    profile=profile,
                    title="mrs",
                    first_name="Next",
                    last_name="Kin",
                    date_of_birth="1980-01-01",
                    gender="female",
                    relationship="Spouse",
                    email_address=f"kin.{prefix}{n}@{domain}",
                    phone_number="+254700000000",
                    address="1 Seed Street",
                    city="Nairobi",
                    country="KE",
                    is_primary=True,
                )
                BankAccount.objects.create(
                    user=user,
                    account_number=generate_account_number(BankAccount.AccountCurrency.DOLLAR),
                    currency=BankAccount.AccountCurrency.DOLLAR,
                    account_type=BankAccount.AccountType.CURRENT,
                    account_balance=opts["balance"],
                    account_status=BankAccount.AccountStatus.ACTIVE,
                    is_primary=True,
                    kyc_submitted=True,
                    kyc_verified=True,
                    fully_activated=True,
                    verification_date=timezone.now(),
                    verification_notes="Seeded for demo / load testing",
                )
            created += 1
        self.stdout.write(self.style.SUCCESS(f"created {created} customer(s); password: {PASSWORD}"))
