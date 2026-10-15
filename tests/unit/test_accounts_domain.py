from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from core_apps.accounts.models import BankAccount, Transaction
from core_apps.accounts.utils import calculate_luhn_check_digit, generate_account_number
from core_apps.cards.utils import generate_card_number, generate_cvv
from tests.conftest import make_account, make_user

pytestmark = pytest.mark.django_db


def luhn_valid(number: str) -> bool:
    total = 0
    for i, d in enumerate(reversed([int(c) for c in number])):
        if i % 2 == 1:
            d *= 2
            d -= 9 if d > 9 else 0
        total += d
    return total % 10 == 0


@pytest.mark.parametrize("currency,code", [("us_dollar", "1"), ("pound_sterling", "2"), ("kenya_shilling", "3")])
def test_account_number_structure(currency, code):
    number = generate_account_number(currency)
    assert len(number) == 16 and number.isdigit()
    assert number.startswith("100" "01" + code)  # bank code + branch code + currency code
    assert luhn_valid(number)


def test_account_number_rejects_unknown_currency():
    with pytest.raises(ValueError):
        generate_account_number("bitcoin")


def test_luhn_check_digit_known_value():
    assert calculate_luhn_check_digit("7992739871") == 3  # the textbook example


def test_card_number_is_luhn_valid_and_16_digits():
    for _ in range(20):
        number = generate_card_number()
        assert len(number) == 16 and number.startswith("41234") and luhn_valid(number)


def test_cvv_is_deterministic_three_digits():
    a = generate_cvv("4123456789012345", "2030-01-01")
    assert a == generate_cvv("4123456789012345", "2030-01-01")
    assert len(a) == 3 and a.isdigit()


@pytest.mark.parametrize("balance,expected", [("0", "0.0050"), ("99999.99", "0.0050"), ("100000", "0.0100"), ("499999.99", "0.0100"), ("500000", "0.0150")])
def test_savings_interest_tiers(balance, expected):
    account = make_account(make_user(), balance=balance, account_type="savings")
    assert account.annual_interest_rate == Decimal(expected)


def test_current_accounts_earn_no_interest():
    account = make_account(make_user(), balance="1000000", account_type="current")
    assert account.annual_interest_rate == Decimal("0.0000")
    assert account.apply_daily_interest() == Decimal("0.00")


def test_daily_interest_is_credited_and_recorded():
    account = make_account(make_user(), balance="36500.00", account_type="savings")
    interest = account.apply_daily_interest()   # 36500 * 0.005 / 365 = 0.50
    account.refresh_from_db()
    assert interest == Decimal("0.50") and account.account_balance == Decimal("36500.50")
    tx = Transaction.objects.get(receiver_account=account)
    assert tx.transaction_type == "interest" and tx.status == "completed" and tx.amount == Decimal("0.50")


def test_negative_balance_is_invalid():
    from django.core.exceptions import ValidationError

    account = make_account(make_user())
    account.account_balance = Decimal("-1")
    with pytest.raises(ValidationError):
        account.clean()


def test_only_one_primary_account_per_user():
    user = make_user()
    first = make_account(user)
    second = BankAccount.objects.create(
        user=user, account_number=generate_account_number("pound_sterling"), currency="pound_sterling",
        account_type="current", is_primary=True,
    )
    first.refresh_from_db()
    assert second.is_primary and not first.is_primary


def test_one_account_per_currency_and_type():
    from django.db import IntegrityError, transaction

    user = make_user()
    make_account(user)
    with pytest.raises(IntegrityError), transaction.atomic():
        make_account(user)
