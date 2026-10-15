from decimal import Decimal

import pytest

from core_apps.cards.models import VirtualCard
from tests.conftest import make_account

pytestmark = pytest.mark.django_db


def test_create_top_up_and_delete_a_virtual_card(as_user, customer):
    acct = make_account(customer, "500.00")
    api = as_user(customer)
    r = api.post("/api/v1/cards/virtual-cards/", {"bank_account_number": acct.account_number}, format="json")
    assert r.status_code in (200, 201), r.content
    card = VirtualCard.objects.get(user=customer)
    assert len(card.card_number) == 16 and len(card.cvv) == 3

    r = api.post(f"/api/v1/cards/virtual-cards/{card.id}/top-up/", {"amount": "100.00"}, format="json")
    assert r.status_code == 200, r.content
    card.refresh_from_db(); acct.refresh_from_db()
    assert card.balance == Decimal("100.00") and acct.account_balance == Decimal("400.00")

    assert api.delete(f"/api/v1/cards/virtual-cards/{card.id}/").status_code in (200, 204)


def test_cvv_is_not_unique_so_many_cards_can_exist(customer, other_customer):
    """cvv used to be unique=True on a 3-digit value: the 36th card or so raised an IntegrityError."""
    from django.utils import timezone

    acct = make_account(customer)
    for i in range(40):
        VirtualCard.objects.create(user=customer, bank_account=acct, card_number=f"41234{i:011d}", cvv="123", expiry_date=timezone.now(), balance=0)
    assert VirtualCard.objects.count() == 40


def test_at_most_three_cards_per_user(as_user, customer):
    acct = make_account(customer)
    api = as_user(customer)
    codes = [api.post("/api/v1/cards/virtual-cards/", {"bank_account_number": acct.account_number}, format="json").status_code for _ in range(4)]
    assert codes[-1] == 400 and all(c in (200, 201) for c in codes[:3])
