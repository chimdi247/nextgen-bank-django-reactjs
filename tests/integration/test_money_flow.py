"""Transfers, withdrawals, deposits and the endpoints added for the UI, through the real API."""
from decimal import Decimal

import pytest
from django.core import mail

from core_apps.accounts.models import BankAccount, Transaction
from tests.conftest import last_otp, make_account, make_user

pytestmark = pytest.mark.django_db


def total_money():
    return sum(a.account_balance for a in BankAccount.objects.all())


def do_transfer(api, sender_acct, receiver_acct, amount, answer="blue"):
    r = api.post("/api/v1/accounts/transfer/initiate/", {"sender_account": sender_acct.account_number, "receiver_account": receiver_acct.account_number, "amount": str(amount), "description": "test"}, format="json")
    if r.status_code != 200:
        return r
    r = api.post("/api/v1/accounts/transfer/verify-security-question/", {"security_answer": answer}, format="json")
    assert r.status_code == 200, r.content
    otp = last_otp(sender_acct.user.email)
    return api.post("/api/v1/accounts/transfer/verify-otp/", {"otp": otp}, format="json")


def test_transfer_moves_money_records_a_transaction_and_sends_receipts(as_user, customer, other_customer):
    a, b = make_account(customer, "1000.00"), make_account(other_customer, "50.00")
    api = as_user(customer)
    r = do_transfer(api, a, b, "250.25")
    assert r.status_code == 201, r.content
    a.refresh_from_db(); b.refresh_from_db()
    assert a.account_balance == Decimal("749.75") and b.account_balance == Decimal("300.25")
    tx = Transaction.objects.get(transaction_type="transfer")
    assert tx.status == "completed" and tx.amount == Decimal("250.25") and tx.sender_account == a and tx.receiver_account == b
    assert any(other_customer.email in m.to for m in mail.outbox), "receiver should get a credit alert"


def test_transfer_with_wrong_security_answer_is_refused(as_user, customer, other_customer):
    a, b = make_account(customer), make_account(other_customer)
    api = as_user(customer)
    api.post("/api/v1/accounts/transfer/initiate/", {"sender_account": a.account_number, "receiver_account": b.account_number, "amount": "10"}, format="json")
    r = api.post("/api/v1/accounts/transfer/verify-security-question/", {"security_answer": "red"}, format="json")
    assert r.status_code >= 400
    a.refresh_from_db()
    assert a.account_balance == Decimal("1000.00")


def test_transfer_with_insufficient_funds_changes_nothing(as_user, customer, other_customer):
    a, b = make_account(customer, "10.00"), make_account(other_customer, "0.00")
    r = do_transfer(as_user(customer), a, b, "500")
    assert r.status_code == 400
    a.refresh_from_db(); b.refresh_from_db()
    assert (a.account_balance, b.account_balance) == (Decimal("10.00"), Decimal("0.00"))
    assert Transaction.objects.count() == 0


def test_cannot_transfer_from_someone_elses_account(as_user, customer, other_customer):
    a, b = make_account(customer), make_account(other_customer)
    r = as_user(other_customer).post("/api/v1/accounts/transfer/initiate/", {"sender_account": a.account_number, "receiver_account": b.account_number, "amount": "10"}, format="json")
    assert r.status_code in (403, 404)


def test_unverified_account_cannot_send(as_user, customer, other_customer):
    a, b = make_account(customer, active=False), make_account(other_customer)
    r = as_user(customer).post("/api/v1/accounts/transfer/initiate/", {"sender_account": a.account_number, "receiver_account": b.account_number, "amount": "10"}, format="json")
    assert r.status_code == 403


def test_many_transfers_conserve_money(as_user, customer, other_customer):
    a, b = make_account(customer, "1000.00"), make_account(other_customer, "1000.00")
    before = total_money()
    for i in range(6):
        sender, receiver, actor = (a, b, customer) if i % 2 == 0 else (b, a, other_customer)
        assert do_transfer(as_user(actor), sender, receiver, f"{10 + i}.50").status_code == 201
    assert total_money() == before


def test_withdrawal_two_step_flow(as_user, customer):
    a = make_account(customer, "300.00")
    api = as_user(customer)
    assert api.post("/api/v1/accounts/initiate-withdrawal/", {"account_number": a.account_number, "amount": "120.00"}, format="json").status_code == 200
    r = api.post("/api/v1/accounts/verify-username-and-withdraw/", {"username": customer.username}, format="json")
    assert r.status_code in (200, 201), r.content
    a.refresh_from_db()
    assert a.account_balance == Decimal("180.00")
    assert Transaction.objects.filter(transaction_type="withdrawal", amount=Decimal("120.00")).exists()


def test_withdrawal_with_wrong_username_is_refused(as_user, customer):
    a = make_account(customer, "300.00")
    api = as_user(customer)
    api.post("/api/v1/accounts/initiate-withdrawal/", {"account_number": a.account_number, "amount": "20"}, format="json")
    assert api.post("/api/v1/accounts/verify-username-and-withdraw/", {"username": "NOT-ME"}, format="json").status_code >= 400
    a.refresh_from_db()
    assert a.account_balance == Decimal("300.00")


def test_teller_deposit_credits_the_account_and_records_a_transaction(as_user, teller, customer):
    a = make_account(customer, "10.00")
    r = as_user(teller).post("/api/v1/accounts/deposit/", {"account_number": a.account_number, "amount": "90.00"}, format="json")
    assert r.status_code in (200, 201), r.content
    a.refresh_from_db()
    assert a.account_balance == Decimal("100.00")
    # deposits used to leave no trace in the history
    tx = Transaction.objects.get(transaction_type="deposit")
    assert tx.receiver_account == a and tx.status == "completed"


def test_customer_cannot_deposit(as_user, customer, other_customer):
    a = make_account(other_customer)
    assert as_user(customer).post("/api/v1/accounts/deposit/", {"account_number": a.account_number, "amount": "5"}, format="json").status_code == 403


def test_branch_manager_may_act_as_teller(as_user, manager, customer):
    a = make_account(customer)
    assert as_user(manager).post("/api/v1/accounts/deposit/", {"account_number": a.account_number, "amount": "5"}, format="json").status_code in (200, 201)


# ---------------------------------------------------------------------------------------- endpoints added for the UI
def test_my_accounts_lists_only_my_accounts(as_user, customer, other_customer):
    mine = make_account(customer, "12.34")
    make_account(other_customer, "99.00")
    r = as_user(customer).get("/api/v1/accounts/")
    assert r.status_code == 200
    rows = r.json()
    assert [x["account_number"] for x in rows] == [mine.account_number]
    assert rows[0]["account_balance"] == "12.34" and rows[0]["fully_activated"] is True


def test_account_lookup_masks_the_holder_and_hides_the_balance(as_user, customer, other_customer):
    other_customer.first_name, other_customer.last_name = "Wanjiku", "Kamau"
    other_customer.save()
    acct = make_account(other_customer, "777.00")
    r = as_user(customer).get("/api/v1/accounts/lookup/", {"account_number": acct.account_number})
    assert r.status_code == 200
    body = r.json()
    assert body["holder_name"] == "Wanjiku K." and "account_balance" not in body and "777" not in str(body)
    assert as_user(customer).get("/api/v1/accounts/lookup/", {"account_number": "0000000000000000"}).status_code == 404
    assert as_user(customer).get("/api/v1/accounts/lookup/").status_code == 400


def test_pending_kyc_queue_is_for_account_executives(as_user, executive, customer, other_customer):
    make_account(customer, active=False)
    make_account(other_customer, active=True)
    assert as_user(customer).get("/api/v1/accounts/pending/").status_code == 403
    r = as_user(executive).get("/api/v1/accounts/pending/")
    assert r.status_code == 200 and r.json()["count"] == 1
    assert as_user(executive).get("/api/v1/accounts/pending/", {"state": "all"}).json()["count"] == 2


def test_kyc_verification_activates_the_account(as_user, executive, customer):
    acct = make_account(customer, active=False)
    r = as_user(executive).patch(f"/api/v1/accounts/verify/{acct.id}/", {"kyc_submitted": True, "kyc_verified": True, "verification_notes": "ok"}, format="json")
    assert r.status_code == 200, r.content
    acct.refresh_from_db()
    assert acct.kyc_verified is True


def test_bank_stats_are_manager_only_and_cached(as_user, manager, customer, teller):
    make_account(customer, "500.00")
    assert as_user(customer).get("/api/v1/accounts/stats/").status_code == 403
    assert as_user(teller).get("/api/v1/accounts/stats/").status_code == 403
    first = as_user(manager).get("/api/v1/accounts/stats/").json()
    assert first["customers"] >= 1 and first["accounts_total"] == 1
    make_account(make_user(), "1.00")
    second = as_user(manager).get("/api/v1/accounts/stats/").json()
    assert second["generated_at"] == first["generated_at"], "served from the cache for 30 s"


def test_transaction_history_lists_both_directions(as_user, customer, other_customer):
    a, b = make_account(customer, "100.00"), make_account(other_customer, "0.00")
    assert do_transfer(as_user(customer), a, b, "5.00").status_code == 201
    mine = as_user(customer).get("/api/v1/accounts/transactions/").json()
    theirs = as_user(other_customer).get("/api/v1/accounts/transactions/").json()
    assert mine["count"] == 1 and theirs["count"] == 1
