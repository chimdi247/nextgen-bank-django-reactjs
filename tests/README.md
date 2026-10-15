# Tests

| Kind | Where | Runs on | Command |
|---|---|---|---|
| **Unit** | `tests/unit` | pytest-django, SQLite, no infrastructure | `make test-unit` |
| **Integration** | `tests/integration` | pytest + DRF test client through the real URL / middleware / auth / DB stack, eager Celery, in-memory mail | `make test-integration` |
| **Selenium (browser E2E)** | `tests/e2e/test_ui_selenium.py` | headless Chrome (`selenium` container) against the running stack | `make test-selenium` |
| **Live API** | `tests/e2e/test_api_live.py` | HTTP against the running stack | `make test-live` |
| **Performance (k6)** | `tests/performance/k6` | k6 in the compose network, metrics streamed to Grafana | `make test-smoke` / `test-load` / ... |

`make test-coverage` prints coverage for unit + integration. Unit and integration tests need **no** running stack
(`config/settings/test.py`: SQLite, locmem cache and mail, eager Celery, MD5 hasher, telemetry off) and also run outside docker:

```bash
pip install -r requirements/test.txt && pytest          # from the repo root (pytest.ini)
```

## Unit tests (`tests/unit`)
User model (username, OTP set/verify/expiry/one-time use, lockout and automatic unlock), account numbers and cards (Luhn,
prefixes, CVV), savings-interest tiers and daily interest, one-primary-account and one-account-per-currency rules, the
role/permission matrix (branch manager supervises staff roles), JSON logging with `trace_id`/`span_id`, the `X-Trace-Id`
middleware, business-metric helpers, and config guards (`DEBUG="False"` parsing, every Celery Beat entry has a schedule,
no per-day throttle limits, gunicorn per-worker telemetry hook).

## Integration tests (`tests/integration`)
* **Auth lifecycle** - register -> activation e-mail -> password step -> OTP e-mail -> cookies (HttpOnly) -> `/me` (role present, no security answer);
  OTP one-time use, expiry, OTP bound to the e-mail, lockout after repeated failures, every protected endpoint rejects anonymous callers.
* **Money** - three-step transfer, wrong security answer, insufficient funds (nothing changes), cannot spend from someone else's account, unverified
  account blocked, **money conservation over many transfers**, two-step withdrawal, teller deposit (now recorded as a transaction), role rules.
* **UI endpoints added to the API** - my accounts, recipient lookup (masked name, no balance), KYC queue, KYC verification, cached bank stats.
* **Onboarding** - photos stored locally without Cloudinary (absolute URLs), account opens automatically when photos, next of kin and account choice are all in (either order), no duplicates.
* **Cards** - create / top-up / delete, max three, many cards no longer collide on the CVV.

## Selenium + live API (`tests/e2e`)
Needs the stack (`make build`) and the demo data (`docker/local/postgres/init/03-demo-data.sql`, loaded on first start).
The tests behave like a person: they read OTP codes and the activation link from **Mailpit** (`http://localhost:8025`).
Covered: login page validation, redirect for anonymous users, admin two-step login and staff menu, System page links, deposit lookup,
**register -> activate -> sign in**, **alice sends money to bob** (security answer + OTP), customers cannot reach staff pages.
Watch the browser live at http://localhost:7900 (password `secret`). Failing tests save screenshots to `tests/results/`.

## Performance tests (`tests/performance`)
`tests/performance/run.sh <test>` seeds verified, funded customers `perf1..perf<N>` (`manage.py seed_demo_data`, idempotent), runs k6 and streams
metrics to Prometheus. Watch live at **http://localhost:3001/d/nb-k6** next to the PostgreSQL / PgBouncer / Redis / RabbitMQ dashboards.

| Test | Question | Default | Pass / fail |
|---|---|---|---|
| `smoke` | alive? auth + authorisation rules right? | 2 VUs, 1 min | every check green |
| `load` | SLOs at expected traffic? | ramp to 20 VUs, hold 5 min | errors < 1 %, balances p95 < 800 ms |
| `stress` | where does it degrade? recovers? | 5 plateaus up to 120 VUs | loose: read the graphs |
| `spike` | sudden 5 -> 150 -> 5 VUs | 20 s spike, 3 min recovery | errors < 5 % |
| `soak` | leaks / queue creep over time | 10 VUs, 1 h (`DURATION=4h`) | errors < 1 %, p95 < 1 s |
| `breakpoint` | maximum throughput | 5 -> 250 it/s, self-aborts at p95 > 2 s | the abort point is the result |
| `otp` | login e-mail chain: API -> RabbitMQ -> Celery -> SMTP -> Mailpit | 5 VUs, 2 min | `otp_delivery_ms` p95 < 8 s |
| `transfers` | row locking + pooling under concurrent real transfers | 5 VUs, 2 min | p95 < 10 s, **sum of balances unchanged** |
| `read-heavy` | read path nginx -> gunicorn -> PgBouncer -> Postgres | 40 VUs | p95 < 600 ms |

Tune with env vars: `LOAD_VUS=50 HOLD=10m make test-load`. `make test-clean` deletes the `perf*` customers.
Notes: the default API throttle is 6000 requests/minute per user (`THROTTLE_USER_RATE`); raise it in `.envs/.env.local` for stress / breakpoint runs.
The CPU / memory alerts (> 40 %) will fire during stress, spike and breakpoint runs; the e-mails appear in Mailpit.
