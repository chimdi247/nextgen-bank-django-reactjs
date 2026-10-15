# NextGen Bank - run everything with one file

```bash
docker compose -f local.yml up --build -d        # or:  make build      (first build takes several minutes; give Docker >= 8 GB RAM)
```
Open **http://localhost:8080** and sign in with `admin@example.com` / `password123`.
**Sign-in is two-step**: after the password an e-mailed code is required. In this environment all e-mail is caught by **Mailpit: http://localhost:8025**.

| What | URL | Login |
|---|---|---|
| **NextGen Bank** (React + shadcn/ui, API behind nginx) | http://localhost:8080 | `admin@example.com` / `password123` (branch manager). Demo customers: `alice@example.com`, `bob@example.com` / `password123` |
| Mailpit (OTP codes, activation links, receipts, Grafana alerts) | http://localhost:8025 | - |
| **Grafana** | http://localhost:3001 | `admin` / `admin` |
| RabbitMQ management | http://localhost:15672 | `rabbit` / `rabbit_local_password` |
| Flower (Celery) | http://localhost:5555 | `flower` / `flower` |
| RedisInsight | http://localhost:5540 | (connection pre-configured) |
| Prometheus / Loki / Tempo | :9090 / :3100 / :3200 | - |
| Postgres (direct) / PgBouncer | :5432 / :6432 | `banker` / `banker_local_password` |
| Django admin | http://localhost:8080/supersecret/ | admin account |

## What you get
```
browser -> nginx :8080 (serves the React build, proxies /api/v1 /supersecret /static /media)
            -> gunicorn (api)  -> PgBouncer (transaction pooling) -> PostgreSQL primary  ==streaming==>  PostgreSQL replica
                               -> Redis (cache + throttling + Celery results)
                               -> RabbitMQ -> Celery worker (e-mails, PDF, photo processing) -> SMTP (Mailpit)
                               Celery beat (daily interest, suspicious-activity scan; exports the business KPI gauges)
```
* `local.yml` (29 services incl. the opt-in `tests` profile) · `docker/local/` (Dockerfiles, nginx, PgBouncer, replica bootstrap, **SQL**) · `.envs/.env.local` (ready to run) ·
  `observability/` · `frontend/` · `tests/`.
* **SQL** (`docker/local/postgres/init`, runs once on an empty volume; re-run with `make down-v`): `00-replication.sh` (replication role + slot),
  `01-schema.sql` (every table, index and constraint + the migration history, so `migrate` is a no-op for the project's apps),
  `02-seed-admin.sql` (**admin@example.com / password123**, stored as a Django PBKDF2 hash that Django upgrades to Argon2 at first login),
  `03-demo-data.sql` (optional: alice and bob with funded accounts and some history).
  `django_celery_beat`'s own tables are created by its library migrations when the api starts (their schema belongs to the package).
* **Roles**: customer, teller, account executive, branch manager. The admin is a branch manager (+ superuser) and may act as any staff role.
  Customer onboarding in the UI: register -> activate (e-mailed link) -> sign in -> Profile & KYC (photos, next of kin, account choice) -> the account opens
  automatically -> an account executive verifies KYC -> a teller deposits cash -> the customer can transfer, withdraw and create virtual cards.

## Observability (OpenTelemetry -> Collector -> Tempo / Loki / Prometheus -> Grafana)
* **Auto-instrumentation**: Django (HTTP spans + RED metrics), psycopg2 (SQL), Redis, Celery (context travels in task headers: one login = one trace across api, RabbitMQ, worker), requests.
  **Manual instrumentation** (`core_apps/common/telemetry.py`): business spans (`bank.transfer.process`, `bank.deposit`, `bank.account.open`, `bank.profile.upload_photos`) and metrics
  (`bank_logins_total`, `bank_otp_verifications_total`, `bank_transactions_total{type,status}`, `bank_transaction_amount` histogram, `bank_accounts_opened_total`, `bank_kyc_decisions_total`,
  `bank_cards_total`, `bank_emails_total`, and DB-backed gauges `bank_users_current`, `bank_accounts_current`, `bank_balance_total`, ... exported by celery-beat only).
* **Logs**: structured JSON on stdout and OTLP -> Loki, with `trace_id` / `span_id`. In Grafana open a log line and click **Open trace in Tempo**; each span has a **Logs** button back.
  Every API response carries `X-Trace-Id`; the UI shows it as `ref …` in error messages.
* **Dashboards** (`observability/grafana/dashboards`, regenerate with `make regenerate-dashboards`): **Platform overview** (uptime, SLI/SLO + error budgets, RED, successful vs failed HTTP, business KPIs, container & node CPU/memory, logs, traces),
  **PostgreSQL** (replication lag, TPS, % of max connections, active connections), **PgBouncer** (client / server connections, waiting clients, % of pool in use),
  **Redis** (connected clients, cache hit ratio, command throughput, memory %), **RabbitMQ & Celery** (messages waiting, published/s, acked/s, unacked), **k6**.
* **Alerts** (Grafana-managed, e-mailed over SMTP; default Mailpit): container / node **CPU and memory above 40 %**, Postgres down, connections > 80 %, replication lag > 30 s, PgBouncer clients waiting, Redis memory > 80 %, RabbitMQ backlog / no consumers.

## What was fixed in the application (it would not have worked end to end otherwise)
* Celery Beat crashed at start (schedule entries had no `schedule`). Login OTP was looked up by code alone (collisions between users); it is now bound to the e-mail. DRF throttle was 100 requests per **day**; `DEBUG="False"` parsed truthy; `COOKIE_SECURE` defaulted to True (cookies dropped on http); `CACHES` was never configured (Redis unused); `compose` network was `external: true`; `.envs/.env.local` did not exist.
* **No API existed to list a user's accounts / balances**: added `GET /accounts/`, `/accounts/lookup/`, `/accounts/pending/` (KYC queue), `/accounts/stats/` (cached in Redis), `/api/v1/health/`; the user serializer now exposes the role and no longer leaks the security answer.
* Money safety: transfers were not atomic and balances were read-modify-write without locks; now one transaction with ordered row locks (`select_for_update`). Deposits created no `Transaction` row; they do now.
* Onboarding: photos needed Cloudinary and were processed **after** the "profile complete?" check, so no account was ever opened; now a local-storage fallback, and the account opens when the last piece arrives (task or next-of-kin). Profile list used `photo.url` (500 without Cloudinary); the large-photo path read a missing key.
* Cards: `cvv` was `unique` on a 3-digit value (collisions after ~35 cards) - migration `cards/0002`. Suspicious-activity task flagged **old** transactions and alerted only for the first account.
* Branch managers now pass teller / account-executive checks (they supervise those roles).

## Notes and limits
* Everything was validated statically (YAML / JSON / TypeScript / Python / JS parsing, SQL insert structure against the DDL, route and import cross-checks). **None of it could be built or run** where it was written (no Docker, Postgres, npm or PyPI access), so expect a first-boot iteration: `docker compose -f local.yml logs <service>`.
  The riskiest pieces: hand-written DDL vs Django 4.2 (compare with `python manage.py sqlmigrate`), OTel metric attribute names (dashboards assume the stable HTTP semconv, `http/dup` also emits the legacy ones), exporter metric names (postgres / pgbouncer exporters), RedisInsight pre-setup file format.
* Replication lag reads 0 while the replica is caught up; "Active connections" is the open backend count (the exporter has no per-state breakdown). `max_connections` (100) and PgBouncer pool size (20) are dashboard constants matching the config.
* Change the seeded password, `.envs/.env.local` secrets and SMTP settings before using this beyond your machine. Production compose (`production.yml`, `docker/production`) was left as it was.
