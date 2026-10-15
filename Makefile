build:
	docker compose -f local.yml up --build -d --remove-orphans

up:
	docker compose -f local.yml up -d

down:
	docker compose -f local.yml down

down-v:
	docker compose -f local.yml down -v

banker-config:
	docker compose -f local.yml config

makemigrations:
	docker compose -f local.yml run --rm api python manage.py makemigrations

migrate:
	docker compose -f local.yml run --rm api python manage.py migrate

collectstatic:
	docker compose -f local.yml run --rm api python manage.py collectstatic --no-input --clear

superuser:
	docker compose -f local.yml run --rm api python manage.py createsuperuser

flush:
	docker compose -f local.yml run --rm api python manage.py flush

network-inspect:
	docker network inspect banker_local_nw

banker-db:
	docker compose -f local.yml exec postgres psql --username=banker --dbname=banker
# ------------------------------------------------------------------ tests (see tests/README.md)
COMPOSE = docker compose -f local.yml

test-unit:                      ## pytest unit tests (SQLite, no infrastructure needed)
	$(COMPOSE) --profile tests run --rm test-runner pytest tests/unit -v

test-integration:               ## pytest API integration tests (real HTTP stack in-process, DB, eager Celery, locmem mail)
	$(COMPOSE) --profile tests run --rm test-runner pytest tests/integration -v

test-coverage:
	$(COMPOSE) --profile tests run --rm test-runner pytest tests/unit tests/integration --cov=core_apps --cov-report=term-missing

test-selenium:                  ## browser tests against the running stack (watch at http://localhost:7900, password: secret)
	$(COMPOSE) --profile tests up -d selenium
	$(COMPOSE) --profile tests run --rm e2e-runner pytest -v -m selenium

test-live:                      ## HTTP checks against the running stack
	$(COMPOSE) --profile tests run --rm e2e-runner pytest -v -m live

test-smoke test-load test-stress test-spike test-soak test-breakpoint test-otp test-transfers test-read-heavy:
	tests/performance/run.sh $(subst test-,,$@)

test-perf-suite:                ## smoke -> load -> spike -> transfers
	tests/performance/run.sh suite

test-clean:                     ## remove the perf* customers created for load tests
	$(COMPOSE) exec api python manage.py seed_demo_data --prefix perf --cleanup

regenerate-dashboards:
	cd observability/grafana && python3 generate_dashboards.py && python3 generate_k6_dashboard.py
