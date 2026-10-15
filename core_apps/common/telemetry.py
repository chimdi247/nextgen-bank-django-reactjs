"""Manual instrumentation of the important business logic.

Library calls (HTTP, SQL, Redis, Celery) are traced automatically by config/telemetry.py. This module adds what no
auto-instrumentation can know: business spans (``bank.transfer.process`` ...), business counters/histograms and
DB-backed KPI gauges. Everything degrades to no-ops when OpenTelemetry is not initialised (tests, management commands).

Metric names (Prometheus form):
  bank_logins_total{outcome}                  bank_otp_verifications_total{outcome}      bank_registrations_total
  bank_transactions_total{type,status}        bank_transaction_amount{type,currency}  (histogram)
  bank_accounts_opened_total{currency,type}   bank_kyc_decisions_total{outcome}
  bank_cards_total{event}                     bank_emails_total{template,outcome}
  bank_users_current{role,status}  bank_accounts_current{status,currency,type}  bank_balance_total{currency}
  bank_cards_current{status}  bank_transactions_pending_current   (gauges, exported by celery beat only)
"""
from contextlib import contextmanager
from decimal import Decimal
from typing import Iterator, Optional

from opentelemetry import metrics, trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer("nextgen.bank")
_meter = metrics.get_meter("nextgen.bank")

_logins = _meter.create_counter("bank.logins", description="Login attempts (password step)")
_otp = _meter.create_counter("bank.otp.verifications", description="OTP verifications")
_registrations = _meter.create_counter("bank.registrations", description="Customer registrations")
_transactions = _meter.create_counter("bank.transactions", description="Transactions by type and status")
_amount = _meter.create_histogram(
    "bank.transaction.amount",
    description="Value of completed transactions",
    explicit_bucket_boundaries_advisory=[1, 10, 50, 100, 500, 1000, 5000, 10000, 50000, 100000],
)
_accounts_opened = _meter.create_counter("bank.accounts.opened", description="Bank accounts opened")
_kyc = _meter.create_counter("bank.kyc.decisions", description="KYC verification decisions")
_cards = _meter.create_counter("bank.cards", description="Virtual card events")
_emails = _meter.create_counter("bank.emails", description="Transactional e-mails")


@contextmanager
def span(name: str, **attributes) -> Iterator[trace.Span]:
    """Business span; records exceptions and marks the span failed."""
    with tracer.start_as_current_span(name) as current:
        for key, value in attributes.items():
            if value is None:
                continue
            current.set_attribute(f"bank.{key}", value if isinstance(value, (int, float, bool, str)) else str(value))
        try:
            yield current
        except Exception as exc:
            current.record_exception(exc)
            current.set_status(Status(StatusCode.ERROR, str(exc)))
            raise


def login(outcome: str) -> None:
    _logins.add(1, {"outcome": outcome})


def otp(outcome: str) -> None:
    _otp.add(1, {"outcome": outcome})


def registration() -> None:
    _registrations.add(1)


def transaction(kind: str, status: str, amount: Optional[Decimal] = None, currency: str = "") -> None:
    _transactions.add(1, {"type": kind, "status": status})
    if amount is not None and status == "completed":
        _amount.record(float(amount), {"type": kind, "currency": currency})


def account_opened(currency: str, account_type: str) -> None:
    _accounts_opened.add(1, {"currency": currency, "type": account_type})


def kyc(outcome: str) -> None:
    _kyc.add(1, {"outcome": outcome})


def card(event: str) -> None:
    _cards.add(1, {"event": event})


def email(template: str, outcome: str) -> None:
    _emails.add(1, {"template": template, "outcome": outcome})


def register_business_gauges() -> None:
    """DB-backed KPI gauges. Registered only in the single celery-beat process, so each series exists once."""
    from django.db import connections
    from django.db.models import Count, Sum

    from core_apps.accounts.models import BankAccount, Transaction
    from core_apps.cards.models import VirtualCard
    from django.contrib.auth import get_user_model

    User = get_user_model()

    def _safe(fn):
        def wrapper(options):
            try:
                yield from fn(options)
            except Exception:  # never let a KPI query break metric export
                return
            finally:
                connections.close_all()  # the reader thread must not keep a connection open

        return wrapper

    def users(_options):
        for row in User.objects.values("role", "account_status").annotate(n=Count("id")):
            yield metrics.Observation(row["n"], {"role": row["role"], "status": row["account_status"]})

    def accounts(_options):
        for row in BankAccount.objects.values("account_status", "currency", "account_type").annotate(n=Count("id")):
            yield metrics.Observation(
                row["n"], {"status": row["account_status"], "currency": row["currency"], "type": row["account_type"]}
            )

    def balances(_options):
        for row in BankAccount.objects.values("currency").annotate(total=Sum("account_balance")):
            yield metrics.Observation(float(row["total"] or 0), {"currency": row["currency"]})

    def cards(_options):
        for row in VirtualCard.objects.values("status").annotate(n=Count("id")):
            yield metrics.Observation(row["n"], {"status": row["status"]})

    def pending(_options):
        yield metrics.Observation(Transaction.objects.filter(status="pending").count())

    _meter.create_observable_gauge("bank.users.current", callbacks=[_safe(users)], description="Users by role and status")
    _meter.create_observable_gauge("bank.accounts.current", callbacks=[_safe(accounts)], description="Accounts")
    _meter.create_observable_gauge("bank.balance.total", callbacks=[_safe(balances)], description="Sum of balances")
    _meter.create_observable_gauge("bank.cards.current", callbacks=[_safe(cards)], description="Virtual cards")
    _meter.create_observable_gauge("bank.transactions.pending.current", callbacks=[_safe(pending)], description="Pending transactions")
