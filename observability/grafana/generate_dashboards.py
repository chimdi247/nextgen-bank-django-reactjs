"""Regenerates every dashboard in dashboards/ (run from observability/grafana:  python3 generate_dashboards.py).
The JSON files are the source of truth for Grafana; this script only keeps the ~300 panels consistent."""
from dash_lib import Board, G, O, R, BLUE, cpu_cores, cpu_pct, mem_bytes, mem_pct, qvar, PROM

RED_GREEN_SLO = [{"color": "red", "value": None}, {"color": "orange", "value": 99}, {"color": "green", "value": 99.9}]
ALERT_STEPS = [G, O, R]   # green < 40 % <= orange < 80 % <= red (the Grafana alerts fire above 40 %)


def rate(metric, sel="", window="$__rate_interval"):
    return "rate(" + metric + "{" + sel + "}[" + window + "])"


# =============================================================================================== overview
SVC = 'service_name=~"$service"'
REQ = "http_server_request_duration_seconds_count{" + SVC + "}"
BUCKET = "http_server_request_duration_seconds_bucket{" + SVC + "}"


def req_rate(codes=None, window="$__rate_interval", by=""):
    sel = SVC + (',http_response_status_code=~"' + codes + '"' if codes else "")
    inner = "http_server_request_duration_seconds_count{" + sel + "}"
    return "sum" + (" by (" + by + ")" if by else "") + "(rate(" + inner + "[" + window + "]))"


def inc(codes, window="$__range"):
    return "sum(increase(http_server_request_duration_seconds_count{" + SVC + ',http_response_status_code=~"' + codes + '"}[' + window + "]))"


b = Board("nb-overview", "NextGen Bank - Platform overview", ["nextgen", "slo", "sli", "otel"], [
    qvar("service", "Service", "label_values(http_server_request_duration_seconds_count, service_name)"),
    {"name": "search", "label": "Log filter", "type": "textbox", "query": "", "current": {"text": "", "value": ""}},
])

b.row("At a glance")
b.stat("Services up", 'sum(probe_success{job=~"blackbox.*"}) or vector(0)', 0, 3,
       steps=[{"color": "red", "value": None}, {"color": "orange", "value": 5}, {"color": "green", "value": 6}],
       desc="HTTP probes succeeding: nginx, frontend, api, mailpit, grafana, rabbitmq (6 expected).")
b.stat("Customers", 'sum(bank_users_current{role="customer"}) or vector(0)', 3, 3, desc="Registered customers (celery-beat exports the KPI gauges).")
b.stat("Bank accounts", "sum(bank_accounts_current) or vector(0)", 6, 3)
b.stat("Total balances (USD)", 'sum(bank_balance_total{currency="us_dollar"}) or vector(0)', 9, 3, unit="currencyUSD")
b.stat("Transactions completed", 'sum(increase(bank_transactions_total{status="completed"}[$__range])) or vector(0)', 12, 3, steps=[{"color": "purple", "value": None}], desc="In the selected time range.")
b.stat("Successful HTTP requests", "(" + inc("[23]..") + ") or vector(0)", 15, 3, steps=[G], desc="2xx / 3xx responses in range.")
b.stat("Failed HTTP requests", "(" + inc("[45]..") + ") or vector(0)", 18, 3, steps=[G, {"color": "orange", "value": 1}, {"color": "red", "value": 50}], desc="4xx / 5xx responses in range.")
b.stat("p95 latency", "histogram_quantile(0.95, sum by (le) (rate(" + BUCKET + "[$__rate_interval])))", 21, 3, unit="s", decimals=3,
       steps=[G, {"color": "orange", "value": 0.5}, {"color": "red", "value": 1}])
b.nxt(4)

b.row("Uptime & availability")
b.stat("Uptime (range)", 'avg(avg_over_time(probe_success{job=~"blackbox.*"}[$__range])) * 100', 0, 4, unit="percent", decimals=3, steps=RED_GREEN_SLO)
b.ts("Service health (1 = up)", [b.tgt('probe_success{job=~"blackbox.*"}', "{{service_name}}")], 4, 10, 6, minv=0, maxv=1.1, fill=20, desc="Blackbox HTTP probes.")
b.ts("Container uptime", [b.tgt('time() - container_start_time_seconds{container_label_com_docker_compose_service!=""}', "{{container_label_com_docker_compose_service}}")], 14, 10, 6, unit="s",
     desc="A sawtooth means the container is restarting.")
b.nxt(6)

b.row("SLI / SLO  (targets: availability 99.9 %, success rate 99 %, latency < 500 ms for 95 % of requests)")
NOT_5XX = "sum(rate(http_server_request_duration_seconds_count{" + SVC + ',http_response_status_code=~"5.."}[$__range])) or vector(0)'
b.stat("Availability SLI (30m)", 'avg(avg_over_time(probe_success{job=~"blackbox.*"}[30m])) * 100', 0, 4, unit="percent", decimals=3, steps=RED_GREEN_SLO, desc="SLO: 99.9 %")
b.stat("Success-rate SLI", "100 * (1 - (" + NOT_5XX + ") / " + req_rate(window="$__range") + ")", 4, 4, unit="percent", decimals=3, steps=RED_GREEN_SLO, desc="Requests that did not fail with 5xx. SLO: 99 %")
b.stat("Latency SLI (< 500 ms)", "100 * sum(rate(http_server_request_duration_seconds_bucket{" + SVC + ',le="0.5"}[$__range])) / ' + req_rate(window="$__range"), 8, 4,
       unit="percent", decimals=2, steps=[{"color": "red", "value": None}, {"color": "orange", "value": 90}, {"color": "green", "value": 95}], desc="SLO: 95 %")
b.stat("Error budget left (availability)", '100 * clamp_min(1 - ((1 - avg(avg_over_time(probe_success{job=~"blackbox.*"}[$__range]))) / 0.001), 0)', 12, 4, unit="percent", decimals=1,
       steps=[{"color": "red", "value": None}, {"color": "orange", "value": 25}, {"color": "green", "value": 60}], desc="1 - observed downtime / allowed downtime of a 99.9 % SLO.")
b.stat("Error budget left (success rate)", "100 * clamp_min(1 - (((" + NOT_5XX + ") / " + req_rate(window="$__range") + ") / 0.01), 0)", 16, 4, unit="percent", decimals=1,
       steps=[{"color": "red", "value": None}, {"color": "orange", "value": 25}, {"color": "green", "value": 60}], desc="1 - observed 5xx ratio / allowed 1 %.")
b.stat("Apdex-style satisfaction", "100 * (sum(rate(http_server_request_duration_seconds_bucket{" + SVC + ',le="0.25"}[$__range])) + (sum(rate(http_server_request_duration_seconds_bucket{' + SVC + ',le=~"1|1.0"}[$__range])) - sum(rate(http_server_request_duration_seconds_bucket{' + SVC + ',le="0.25"}[$__range]))) / 2) / ' + req_rate(window="$__range"), 20, 4,
       unit="percent", decimals=1, steps=[{"color": "red", "value": None}, {"color": "orange", "value": 70}, {"color": "green", "value": 85}], desc="Satisfied < 250 ms, tolerating < 1 s.")
b.nxt(4)
b.ts("Success rate by service (non-5xx, 5m)", [b.tgt("100 * (1 - (sum by (service_name) (rate(http_server_request_duration_seconds_count{" + SVC + ',http_response_status_code=~"5.."}[5m])) or (0 * sum by (service_name) (rate(' + REQ + "[5m])))) / sum by (service_name) (rate(" + REQ + "[5m])))", "{{service_name}}")],
     0, 12, 7, unit="percent", minv=90, maxv=100, steps=[{"color": "red", "value": None}, {"color": "green", "value": 99}])
b.ts("Latency SLI by service (% < 500 ms, 5m)", [b.tgt("100 * sum by (service_name) (rate(http_server_request_duration_seconds_bucket{" + SVC + ',le="0.5"}[5m])) / sum by (service_name) (rate(' + REQ + "[5m]))", "{{service_name}}")],
     12, 12, 7, unit="percent", minv=0, maxv=100, steps=[{"color": "red", "value": None}, {"color": "green", "value": 95}])
b.nxt(7)

b.row("Traffic, errors & latency (RED)")
b.ts("Request rate by service", [b.tgt(req_rate(by="service_name"), "{{service_name}}")], 0, 8, 8, unit="reqps", stack=True)
b.ts("Requests by status class", [b.tgt(req_rate("2.."), "2xx", "A"), b.tgt(req_rate("3.."), "3xx", "B"), b.tgt(req_rate("4.."), "4xx", "C"), b.tgt(req_rate("5.."), "5xx", "D")], 8, 8, 8, unit="reqps", stack=True)
b.ts("Error rate % (4xx + 5xx)", [b.tgt("100 * sum by (service_name) (rate(http_server_request_duration_seconds_count{" + SVC + ',http_response_status_code=~"[45].."}[$__rate_interval])) / sum by (service_name) (rate(' + REQ + "[$__rate_interval]))", "{{service_name}}")], 16, 8, 8, unit="percent", minv=0)
b.nxt(8)
QUANT = lambda q, by="": "histogram_quantile(" + q + ", sum by (le" + (", " + by if by else "") + ") (rate(" + BUCKET + "[$__rate_interval])))"
b.ts("Latency p50 / p95 / p99", [b.tgt(QUANT("0.50"), "p50", "A"), b.tgt(QUANT("0.95"), "p95", "B"), b.tgt(QUANT("0.99"), "p99", "C")], 0, 8, 8, unit="s")
b.ts("p95 latency by service", [b.tgt(QUANT("0.95", "service_name"), "{{service_name}}")], 8, 8, 8, unit="s")
b.ts("Slowest routes (p95)", [b.tgt("topk(8, " + QUANT("0.95", "http_route") + ")", "{{http_route}}")], 16, 8, 8, unit="s")
b.nxt(8)

b.row("Business KPIs")
TX = "bank_transactions_total"
b.stat("Customers", 'sum(bank_users_current{role="customer"}) or vector(0)', 0, 3)
b.stat("Locked users", 'sum(bank_users_current{status="locked"}) or vector(0)', 3, 3, steps=[G, {"color": "orange", "value": 1}])
b.stat("Active accounts", 'sum(bank_accounts_current{status="active"}) or vector(0)', 6, 3, steps=[{"color": "green", "value": None}])
b.stat("Accounts awaiting KYC", 'sum(bank_accounts_current{status!="active"}) or vector(0)', 9, 3, steps=[G, {"color": "orange", "value": 5}, {"color": "red", "value": 25}], desc="Opened but not yet verified by an account executive.")
b.stat("Transactions completed", "sum(increase(" + TX + '{status="completed"}[$__range])) or vector(0)', 12, 3, steps=[{"color": "green", "value": None}])
b.stat("Failed transactions", "sum(increase(" + TX + '{status="failed"}[$__range])) or vector(0)', 15, 3, steps=[G, {"color": "orange", "value": 1}, {"color": "red", "value": 10}], desc="Insufficient funds, rejected or errored (range).")
b.stat("Transaction value (range)", 'sum(increase(bank_transaction_amount_sum[$__range])) or vector(0)', 18, 3, unit="short", steps=[{"color": "purple", "value": None}], desc="Sum of completed transactions across currencies.")
b.stat("Login success ratio", '100 * sum(increase(bank_otp_verifications_total{outcome="success"}[$__range])) / sum(increase(bank_logins_total{outcome="otp_sent"}[$__range]))', 21, 3, unit="percent", decimals=1,
       steps=[{"color": "red", "value": None}, {"color": "orange", "value": 70}, {"color": "green", "value": 90}], desc="Completed two-step logins / password steps that sent an OTP.")
b.nxt(4)
b.ts("Customers & accounts", [b.tgt('sum(bank_users_current{role="customer"})', "customers", "A"), b.tgt("sum(bank_accounts_current)", "accounts", "B")], 0, 6, 7)
b.ts("Balances by currency", [b.tgt("sum by (currency) (bank_balance_total)", "{{currency}}")], 6, 6, 7, stack=True)
b.ts("Transactions / min by type", [b.tgt("sum by (type, status) (rate(" + TX + "[$__rate_interval])) * 60", "{{type}} {{status}}")], 12, 6, 7, bars=True, stack=True, fill=70)
b.ts("Average ticket by type", [b.tgt("sum by (type) (rate(bank_transaction_amount_sum[5m])) / sum by (type) (rate(bank_transaction_amount_count[5m]))", "{{type}}")], 18, 6, 7)
b.nxt(7)
b.ts("Logins / min (password step)", [b.tgt("sum by (outcome) (rate(bank_logins_total[$__rate_interval])) * 60", "{{outcome}}")], 0, 6, 7, bars=True, stack=True, fill=70)
b.ts("OTP verifications / min", [b.tgt("sum by (outcome) (rate(bank_otp_verifications_total[$__rate_interval])) * 60", "{{outcome}}")], 6, 6, 7, bars=True, stack=True, fill=70)
b.ts("Registrations, accounts opened, KYC decisions / hour", [
    b.tgt("sum(increase(bank_registrations_total[1h]))", "registrations", "A"),
    b.tgt("sum(increase(bank_accounts_opened_total[1h]))", "accounts opened", "B"),
    b.tgt("sum(increase(bank_kyc_decisions_total[1h]))", "KYC decisions", "C")], 12, 6, 7)
b.ts("Cards & e-mails / min", [
    b.tgt("sum by (event) (rate(bank_cards_total[$__rate_interval])) * 60", "card {{event}}", "A"),
    b.tgt("sum by (template, outcome) (rate(bank_emails_total[$__rate_interval])) * 60", "email {{template}} {{outcome}}", "B")], 18, 6, 7)
b.nxt(7)

b.row("Container & node utilisation  (Grafana alerts fire above 40 %)")
NODE_CPU = '100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[2m])) * 100)'
NODE_MEM = "100 * (1 - sum(node_memory_MemAvailable_bytes) / sum(node_memory_MemTotal_bytes))"
b.gauge("Node CPU", NODE_CPU, 0, 4, 6)
b.gauge("Node memory", NODE_MEM, 4, 4, 6)
b.stat("Node disk used", '100 * (1 - sum(node_filesystem_avail_bytes{mountpoint="/"}) / sum(node_filesystem_size_bytes{mountpoint="/"}))', 8, 4, h=6, unit="percent", decimals=1, steps=[G, {"color": "orange", "value": 70}, {"color": "red", "value": 85}])
b.stat("Containers above 40 % CPU", "count((" + cpu_pct() + ") > 40) or vector(0)", 12, 6, h=6, steps=[G, {"color": "red", "value": 1}])
b.stat("Containers above 40 % memory", "count((" + mem_pct() + ") > 40) or vector(0)", 18, 6, h=6, steps=[G, {"color": "red", "value": 1}])
b.nxt(6)
b.ts("Container CPU % of limit", [b.tgt(cpu_pct(), "{{service}}")], 0, 12, 8, unit="percent", steps=ALERT_STEPS, minv=0, desc="Alert: > 40 % for 2 min")
b.ts("Container memory % of limit", [b.tgt(mem_pct(), "{{service}}")], 12, 12, 8, unit="percent", steps=ALERT_STEPS, minv=0, desc="Alert: > 40 % for 2 min")
b.nxt(8)
b.ts("Container memory (working set)", [b.tgt(mem_bytes(".+"), "{{service}}")], 0, 8, 8, unit="bytes")
b.ts("Container CPU (cores)", [b.tgt(cpu_cores(".+"), "{{service}}")], 8, 8, 8)
b.ts("Node CPU % / memory %", [b.tgt(NODE_CPU, "CPU", "A"), b.tgt(NODE_MEM, "Memory", "B")], 16, 8, 8, unit="percent", steps=ALERT_STEPS, minv=0, maxv=100)
b.nxt(8)

b.row("Python runtime (per service)")
b.ts("Gunicorn / Celery processes reporting", [b.tgt("count by (service_name) (count by (service_name, service_instance_id) (http_server_request_duration_seconds_count) )", "{{service_name}}")], 0, 8, 6,
     desc="Distinct worker processes that exported HTTP metrics.")
b.ts("Active HTTP requests", [b.tgt("sum by (service_name) (http_server_active_requests)", "{{service_name}}")], 8, 8, 6)
b.ts("Celery tasks by outcome / min (Flower)", [b.tgt('sum by (type) (rate(flower_events_total{type=~"task-(succeeded|failed|retried)"}[$__rate_interval])) * 60', "{{type}}")], 16, 8, 6, bars=True, stack=True, fill=70)
b.nxt(6)

b.row("Logs & traces  (open a log line, then click \"Open trace in Tempo\" to see the full trace with its spans)")
b.logs("Logs ($service)", '{service_name=~"$service"} |~ "(?i)$search"')
b.nxt(12)
b.traces("Recent error traces", '{ resource.service.name =~ "$service" && status = error }', 0, 12)
b.traces("Slowest traces (> 500 ms)", '{ resource.service.name =~ "$service" && duration > 500ms }', 12, 12)
b.nxt(10)
b.service_map()
b.nxt(10)
b.save("dashboards/nb-overview.json")


# =============================================================================================== PostgreSQL
D = 'datname=~"$db"'
MAXC = "$max_connections"
p = Board("nb-postgres", "NextGen Bank - PostgreSQL", ["nextgen", "postgres", "database"], [
    qvar("db", "Database", 'label_values(pg_stat_database_numbackends{datname!~"template.*|postgres"}, datname)'),
    {"name": "max_connections", "type": "constant", "query": "100", "hide": 2, "skipUrlSync": True, "label": "max_connections"},
])
p.row("Key indicators")
p.stat("Postgres up", 'pg_up{job="postgres"}', 0, 3, steps=[{"color": "red", "value": None}, {"color": "green", "value": 1}])
p.stat("Active connections", "sum(pg_stat_database_numbackends{" + D + "})", 3, 3, steps=[G, {"color": "orange", "value": 60}, {"color": "red", "value": 80}],
       desc="Open backends of the selected databases (what PgBouncer holds open towards Postgres).")
p.stat("% of max connections in use", "100 * sum(pg_stat_database_numbackends{job=\"postgres\"}) / " + MAXC, 6, 3, unit="percent", decimals=1,
       steps=[G, {"color": "orange", "value": 60}, {"color": "red", "value": 80}], desc="All databases vs max_connections (set in local.yml: 100). Alert above 80 %.")
p.stat("Transactions / s (TPS)", "sum(rate(pg_stat_database_xact_commit{" + D + "}[$__rate_interval]) + rate(pg_stat_database_xact_rollback{" + D + "}[$__rate_interval]))", 9, 3, unit="ops", decimals=1)
p.stat("Replication lag", 'max(pg_replication_lag_seconds{job="postgres-replica"})', 12, 3, unit="s", decimals=2, steps=[G, {"color": "orange", "value": 5}, {"color": "red", "value": 30}],
       desc="Seconds the streaming replica is behind the primary (0 when caught up). Alert above 30 s.")
p.stat("Replica up / in recovery", 'min(pg_up{job="postgres-replica"}) * max(pg_replication_is_replica{job="postgres-replica"})', 15, 3, steps=[{"color": "red", "value": None}, {"color": "green", "value": 1}], desc="1 = replica is running and in recovery mode.")
p.stat("Cache hit ratio", "100 * sum(rate(pg_stat_database_blks_hit{" + D + "}[$__range])) / (sum(rate(pg_stat_database_blks_hit{" + D + "}[$__range])) + sum(rate(pg_stat_database_blks_read{" + D + "}[$__range])))", 18, 3,
       unit="percent", decimals=2, steps=[{"color": "red", "value": None}, {"color": "orange", "value": 90}, {"color": "green", "value": 99}])
p.stat("Deadlocks (range)", "sum(increase(pg_stat_database_deadlocks{" + D + "}[$__range]))", 21, 3, steps=[G, {"color": "red", "value": 1}])
p.nxt(4)

p.row("Connections & transactions")
p.ts("Active connections by database", [p.tgt("sum by (datname) (pg_stat_database_numbackends{" + D + "})", "{{datname}}")], 0, 8, 7, stack=True)
p.ts("% of max connections in use", [p.tgt("100 * sum(pg_stat_database_numbackends{job=\"postgres\"}) / " + MAXC, "in use %")], 8, 8, 7, unit="percent", minv=0, maxv=100, steps=[G, {"color": "orange", "value": 60}, {"color": "red", "value": 80}])
p.ts("Transactions per second", [
    p.tgt("sum by (datname) (rate(pg_stat_database_xact_commit{" + D + "}[$__rate_interval]))", "commit {{datname}}", "A"),
    p.tgt("sum by (datname) (rate(pg_stat_database_xact_rollback{" + D + "}[$__rate_interval]))", "rollback {{datname}}", "B")], 16, 8, 7, unit="ops")
p.nxt(7)

p.row("Replication")
p.ts("Replication lag (seconds)", [p.tgt('pg_replication_lag_seconds{job="postgres-replica"}', "replica lag")], 0, 12, 7, unit="s", minv=0, steps=[G, {"color": "orange", "value": 5}, {"color": "red", "value": 30}],
     desc="Measured on the replica: 0 while it has replayed everything it received.")
p.ts("Primary vs replica: rows read / s", [
    p.tgt('sum(rate(pg_stat_database_tup_returned{job="postgres"}[$__rate_interval]))', "primary", "A"),
    p.tgt('sum(rate(pg_stat_database_tup_returned{job="postgres-replica"}[$__rate_interval]))', "replica", "B")], 12, 12, 7, unit="ops")
p.nxt(7)

p.row("Throughput, cache & locks")
p.ts("Rows written / s", [
    p.tgt("sum by (datname) (rate(pg_stat_database_tup_inserted{" + D + "}[$__rate_interval]))", "insert {{datname}}", "A"),
    p.tgt("sum by (datname) (rate(pg_stat_database_tup_updated{" + D + "}[$__rate_interval]))", "update {{datname}}", "B"),
    p.tgt("sum by (datname) (rate(pg_stat_database_tup_deleted{" + D + "}[$__rate_interval]))", "delete {{datname}}", "C")], 0, 8, 7, unit="ops")
p.ts("Cache hit ratio", [p.tgt("100 * sum by (datname) (rate(pg_stat_database_blks_hit{" + D + "}[$__rate_interval])) / (sum by (datname) (rate(pg_stat_database_blks_hit{" + D + "}[$__rate_interval])) + sum by (datname) (rate(pg_stat_database_blks_read{" + D + "}[$__rate_interval])))", "{{datname}}")],
     8, 8, 7, unit="percent", minv=0, maxv=100, steps=[{"color": "red", "value": None}, {"color": "green", "value": 95}])
p.ts("Locks by mode", [p.tgt("sum by (mode) (pg_locks_count{" + D + "})", "{{mode}}")], 16, 8, 7, stack=True)
p.nxt(7)
p.ts("Rows per table (live tuples)", [p.tgt("sum by (relname) (pg_stat_user_tables_n_live_tup{" + D + "})", "{{relname}}")], 0, 8, 7, desc="accounts_transaction, accounts_bankaccount, user_auth_user ...")
p.ts("Database size", [p.tgt("pg_database_size_bytes{" + D + "}", "{{datname}}")], 8, 8, 7, unit="bytes")
p.ts("Long-running transactions / dead tuples", [
    p.tgt('sum(pg_long_running_transactions{job="postgres"})', "long-running transactions", "A"),
    p.tgt("sum(pg_stat_user_tables_n_dead_tup{" + D + "})", "dead tuples", "B")], 16, 8, 7)
p.nxt(7)

p.row("Containers (cAdvisor)")
p.ts("CPU % of limit", [p.tgt(cpu_pct("postgres|postgres-replica"), "{{service}}")], 0, 8, 7, unit="percent", steps=ALERT_STEPS, minv=0)
p.ts("Memory % of limit", [p.tgt(mem_pct("postgres|postgres-replica"), "{{service}}")], 8, 8, 7, unit="percent", steps=ALERT_STEPS, minv=0)
p.ts("Disk I/O", [
    p.tgt('sum by (container_label_com_docker_compose_service) (rate(container_fs_writes_bytes_total{container_label_com_docker_compose_service=~"postgres|postgres-replica"}[$__rate_interval]))', "write {{container_label_com_docker_compose_service}}", "A"),
    p.tgt('sum by (container_label_com_docker_compose_service) (rate(container_fs_reads_bytes_total{container_label_com_docker_compose_service=~"postgres|postgres-replica"}[$__rate_interval]))', "read {{container_label_com_docker_compose_service}}", "B")], 16, 8, 7, unit="Bps")
p.nxt(7)
p.save("dashboards/nb-postgres.json")


# =============================================================================================== PgBouncer
POOL = "$pool_size"
g = Board("nb-pgbouncer", "NextGen Bank - PgBouncer", ["nextgen", "pgbouncer", "database"], [
    {"name": "pool_size", "type": "constant", "query": "20", "hide": 2, "skipUrlSync": True, "label": "default_pool_size"},
])
CLIENT_ACTIVE = "sum(pgbouncer_pools_client_active_connections)"
CLIENT_WAIT = "sum(pgbouncer_pools_client_waiting_connections)"
SERVER_ACTIVE = "sum(pgbouncer_pools_server_active_connections)"
g.row("Key indicators")
g.stat("PgBouncer up", "pgbouncer_up", 0, 3, steps=[{"color": "red", "value": None}, {"color": "green", "value": 1}])
g.stat("Client connections (active)", CLIENT_ACTIVE, 3, 3, steps=[{"color": "blue", "value": None}], desc="Application connections currently running a transaction.")
g.stat("Server connections (in use)", SERVER_ACTIVE, 6, 3, steps=[G, {"color": "orange", "value": 12}, {"color": "red", "value": 18}], desc="Connections PgBouncer holds open to Postgres that are executing a transaction.")
g.stat("Clients waiting for a server connection", CLIENT_WAIT, 9, 3, steps=[G, {"color": "orange", "value": 1}, {"color": "red", "value": 5}], desc="> 0 means the pool is exhausted and requests queue. Alert above 0 for 2 min.")
g.stat("Pool in use %", "100 * " + SERVER_ACTIVE + " / " + POOL, 12, 3, unit="percent", decimals=1, steps=[G, {"color": "orange", "value": 60}, {"color": "red", "value": 85}], desc="Active server connections / default_pool_size (20, set in .envs/.env.local).")
g.stat("Idle server connections", "sum(pgbouncer_pools_server_idle_connections)", 15, 3, steps=[{"color": "blue", "value": None}])
g.stat("Longest client wait", "max(pgbouncer_pools_client_maxwait_seconds)", 18, 3, unit="s", decimals=2, steps=[G, {"color": "orange", "value": 0.5}, {"color": "red", "value": 2}])
g.stat("Queries / s", "sum(rate(pgbouncer_stats_queries_pooled_total[$__rate_interval]))", 21, 3, unit="ops", decimals=1)
g.nxt(4)
g.row("Client side (Django / Celery)")
g.ts("Client connections", [
    g.tgt("sum(pgbouncer_pools_client_active_connections)", "active", "A"),
    g.tgt("sum(pgbouncer_pools_client_waiting_connections)", "waiting", "B"),
    g.tgt("sum(pgbouncer_pools_client_active_connections) + sum(pgbouncer_pools_client_waiting_connections)", "total", "C")], 0, 12, 8)
g.ts("Clients waiting for a server connection", [g.tgt(CLIENT_WAIT, "waiting"), g.tgt("max(pgbouncer_pools_client_maxwait_seconds)", "longest wait (s)", "B")], 12, 12, 8, minv=0,
     steps=[G, {"color": "red", "value": 1}], desc="Queueing here is the first sign the pool is too small.")
g.nxt(8)
g.row("Server side (PostgreSQL)")
g.ts("Server connections", [
    g.tgt(SERVER_ACTIVE, "active", "A"),
    g.tgt("sum(pgbouncer_pools_server_idle_connections)", "idle", "B"),
    g.tgt("sum(pgbouncer_pools_server_used_connections)", "used (waiting for reset)", "C")], 0, 12, 8, stack=True)
g.ts("Percentage of the connection pool in use", [g.tgt("100 * " + SERVER_ACTIVE + " / " + POOL, "pool in use %"),
                                                   g.tgt("100 * (" + SERVER_ACTIVE + " + sum(pgbouncer_pools_server_idle_connections) + sum(pgbouncer_pools_server_used_connections)) / " + POOL, "pool open %", "B")],
     12, 12, 8, unit="percent", minv=0, steps=[G, {"color": "orange", "value": 60}, {"color": "red", "value": 85}])
g.nxt(8)
g.row("Efficiency")
g.ts("Multiplexing: app clients served per Postgres connection", [g.tgt("(" + CLIENT_ACTIVE + " + " + CLIENT_WAIT + ") / clamp_min(" + SERVER_ACTIVE + ", 1)", "clients per server connection")], 0, 8, 7)
g.ts("Queries / s and traffic", [
    g.tgt("sum(rate(pgbouncer_stats_queries_pooled_total[$__rate_interval]))", "queries/s", "A"),
    g.tgt("sum(rate(pgbouncer_stats_received_bytes_total[$__rate_interval]))", "bytes in /s", "B"),
    g.tgt("sum(rate(pgbouncer_stats_sent_bytes_total[$__rate_interval]))", "bytes out /s", "C")], 8, 8, 7)
g.ts("PgBouncer container CPU % / memory %", [g.tgt(cpu_pct("pgbouncer"), "cpu {{service}}", "A"), g.tgt(mem_pct("pgbouncer"), "mem {{service}}", "B")], 16, 8, 7, unit="percent", steps=ALERT_STEPS, minv=0)
g.nxt(7)
g.save("dashboards/nb-pgbouncer.json")


# =============================================================================================== Redis
r = Board("nb-redis", "NextGen Bank - Redis", ["nextgen", "redis", "cache"], [])
HITS, MISSES = "rate(redis_keyspace_hits_total[$__rate_interval])", "rate(redis_keyspace_misses_total[$__rate_interval])"
r.row("Key indicators")
r.stat("Redis up", "redis_up", 0, 3, steps=[{"color": "red", "value": None}, {"color": "green", "value": 1}])
r.stat("Connected clients", "redis_connected_clients", 3, 3, steps=[{"color": "blue", "value": None}])
r.stat("Cache hit ratio", "100 * sum(rate(redis_keyspace_hits_total[$__range])) / (sum(rate(redis_keyspace_hits_total[$__range])) + sum(rate(redis_keyspace_misses_total[$__range])))", 6, 3, unit="percent", decimals=1,
       steps=[{"color": "red", "value": None}, {"color": "orange", "value": 50}, {"color": "green", "value": 80}], desc="hits / (hits + misses). Throttling counters miss on first use, so a healthy API sits well below 100 %.")
r.stat("Commands / s", "rate(redis_commands_processed_total[$__rate_interval])", 9, 3, unit="ops", decimals=1)
r.stat("Memory used %", "100 * redis_memory_used_bytes / redis_memory_max_bytes", 12, 3, unit="percent", decimals=1, steps=[G, {"color": "orange", "value": 70}, {"color": "red", "value": 90}], desc="used_memory / maxmemory (256 MB, allkeys-lru). Alert above 80 %.")
r.stat("Keys", "sum(redis_db_keys)", 15, 3, steps=[{"color": "blue", "value": None}])
r.stat("Evicted keys (range)", "increase(redis_evicted_keys_total[$__range])", 18, 3, steps=[G, {"color": "orange", "value": 1}])
r.stat("Uptime", "redis_uptime_in_seconds", 21, 3, unit="s")
r.nxt(4)
r.row("Clients & throughput")
r.ts("Connected clients", [r.tgt("redis_connected_clients", "connected", "A"), r.tgt("redis_blocked_clients", "blocked", "B")], 0, 8, 7)
r.ts("Command throughput (commands / s)", [r.tgt("rate(redis_commands_processed_total[$__rate_interval])", "all commands")], 8, 8, 7, unit="ops")
r.ts("Top commands / s", [r.tgt("topk(6, sum by (cmd) (rate(redis_commands_total[$__rate_interval])))", "{{cmd}}")], 16, 8, 7, unit="ops")
r.nxt(7)
r.row("Cache effectiveness")
r.ts("Cache hit ratio (%)", [r.tgt("100 * " + HITS + " / (" + HITS + " + " + MISSES + ")", "hit ratio")], 0, 8, 7, unit="percent", minv=0, maxv=100)
r.ts("Keyspace hits vs misses / s", [r.tgt(HITS, "hits", "A"), r.tgt(MISSES, "misses", "B")], 8, 8, 7, unit="ops")
r.ts("Expired / evicted keys / s", [r.tgt("rate(redis_expired_keys_total[$__rate_interval])", "expired", "A"), r.tgt("rate(redis_evicted_keys_total[$__rate_interval])", "evicted", "B")], 16, 8, 7, unit="ops")
r.nxt(7)
r.row("Memory & network")
r.ts("Memory usage (%)", [r.tgt("100 * redis_memory_used_bytes / redis_memory_max_bytes", "used / maxmemory")], 0, 8, 7, unit="percent", minv=0, maxv=100, steps=[G, {"color": "orange", "value": 70}, {"color": "red", "value": 90}])
r.ts("Memory (bytes)", [r.tgt("redis_memory_used_bytes", "used", "A"), r.tgt("redis_memory_max_bytes", "max", "B"), r.tgt("redis_memory_used_rss_bytes", "rss", "C")], 8, 8, 7, unit="bytes")
r.ts("Network I/O", [r.tgt("rate(redis_net_input_bytes_total[$__rate_interval])", "in", "A"), r.tgt("rate(redis_net_output_bytes_total[$__rate_interval])", "out", "B")], 16, 8, 7, unit="Bps")
r.nxt(7)
r.ts("Redis container CPU % / memory %", [r.tgt(cpu_pct("redis"), "cpu {{service}}", "A"), r.tgt(mem_pct("redis"), "mem {{service}}", "B")], 0, 12, 7, unit="percent", steps=ALERT_STEPS, minv=0)
r.ts("Throttling in action: API requests / s vs Redis commands / s", [
    r.tgt('sum(rate(http_server_request_duration_seconds_count{service_name="nextgen-api"}[$__rate_interval]))', "API requests", "A"),
    r.tgt("rate(redis_commands_processed_total[$__rate_interval])", "Redis commands", "B")], 12, 12, 7, unit="ops")
r.nxt(7)
r.save("dashboards/nb-redis.json")


# =============================================================================================== RabbitMQ + Celery
q = Board("nb-rabbitmq", "NextGen Bank - RabbitMQ & Celery", ["nextgen", "rabbitmq", "celery", "messaging"], [
    qvar("queue", "Queue", "label_values(rabbitmq_queue_messages_ready, queue)"),
])
PUB = "sum(rate(rabbitmq_channel_messages_published_total[$__rate_interval]))"
ACK = "sum(rate(rabbitmq_channel_messages_acked_total[$__rate_interval]))"
q.row("Key indicators")
q.stat("RabbitMQ up", 'probe_success{job="blackbox-rabbitmq"}', 0, 3, steps=[{"color": "red", "value": None}, {"color": "green", "value": 1}])
q.stat("Messages waiting in queues", "sum(rabbitmq_queue_messages_ready)", 3, 3, steps=[G, {"color": "orange", "value": 50}, {"color": "red", "value": 200}], desc="Ready messages (published, not yet delivered to a consumer). Alert above 100 for 5 min.")
q.stat("Delivered, not yet acknowledged", "sum(rabbitmq_queue_messages_unacked)", 6, 3, steps=[G, {"color": "orange", "value": 20}, {"color": "red", "value": 100}], desc="Unacked: in the hands of a consumer (a Celery worker) that has not finished.")
q.stat("Published / s", PUB, 9, 3, unit="ops", decimals=2)
q.stat("Acknowledged / s", ACK, 12, 3, unit="ops", decimals=2)
q.stat("Consumers", "sum(rabbitmq_consumers)", 15, 3, steps=[{"color": "red", "value": None}, {"color": "green", "value": 1}], desc="0 means no worker is consuming: tasks pile up.")
q.stat("Connections / channels", "sum(rabbitmq_connections)", 18, 3, steps=[{"color": "blue", "value": None}])
q.stat("Celery workers online", "sum(flower_worker_online)", 21, 3, steps=[{"color": "red", "value": None}, {"color": "green", "value": 1}])
q.nxt(4)
q.row("Queues")
q.ts("Messages waiting in queues (ready)", [q.tgt("sum by (queue) (rabbitmq_queue_messages_ready{queue=~\"$queue\"})", "{{queue}}")], 0, 12, 7, minv=0, steps=[G, {"color": "orange", "value": 100}])
q.ts("Delivered but not acknowledged (unacked)", [q.tgt("sum by (queue) (rabbitmq_queue_messages_unacked{queue=~\"$queue\"})", "{{queue}}")], 12, 12, 7, minv=0)
q.nxt(7)
q.row("Rates")
q.ts("Messages published per second", [q.tgt(PUB, "published")], 0, 8, 7, unit="ops")
q.ts("Messages acknowledged per second", [q.tgt(ACK, "acked", "A"), q.tgt("sum(rate(rabbitmq_channel_messages_delivered_total[$__rate_interval]))", "delivered", "B"), q.tgt("sum(rate(rabbitmq_channel_messages_redelivered_total[$__rate_interval]))", "redelivered", "C")], 8, 8, 7, unit="ops")
q.ts("Published vs acknowledged (backlog builds when published > acked)", [q.tgt(PUB, "published", "A"), q.tgt(ACK, "acked", "B")], 16, 8, 7, unit="ops")
q.nxt(7)
q.row("Broker health")
q.ts("Connections, channels, consumers", [q.tgt("sum(rabbitmq_connections)", "connections", "A"), q.tgt("sum(rabbitmq_channels)", "channels", "B"), q.tgt("sum(rabbitmq_consumers)", "consumers", "C")], 0, 8, 7)
q.ts("Broker memory & file descriptors", [q.tgt("rabbitmq_process_resident_memory_bytes", "resident memory", "A")], 8, 8, 7, unit="bytes")
q.ts("RabbitMQ container CPU % / memory %", [q.tgt(cpu_pct("rabbitmq"), "cpu {{service}}", "A"), q.tgt(mem_pct("rabbitmq"), "mem {{service}}", "B")], 16, 8, 7, unit="percent", steps=ALERT_STEPS, minv=0)
q.nxt(7)
q.row("Celery (Flower)")
q.ts("Tasks / min by outcome", [q.tgt("sum by (type) (rate(flower_events_total{type=~\"task-.*\"}[$__rate_interval])) * 60", "{{type}}")], 0, 8, 7, bars=True, stack=True, fill=70)
q.ts("Task runtime p95 by task", [q.tgt("histogram_quantile(0.95, sum by (le, task) (rate(flower_task_runtime_seconds_bucket[5m])))", "{{task}}")], 8, 8, 7, unit="s")
q.ts("Tasks currently executing", [q.tgt("sum by (worker) (flower_worker_number_of_currently_executing_tasks)", "{{worker}}")], 16, 8, 7)
q.nxt(7)
q.save("dashboards/nb-rabbitmq.json")
