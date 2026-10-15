"""k6 test-run dashboard (run from observability/grafana:  python3 generate_k6_dashboard.py).
k6 pushes its metrics to Prometheus (experimental-prometheus-rw); this board shows them next to what the platform
experienced at the same moment, so a load test can be read as cause -> effect."""
from dash_lib import Board, G, O, R, cpu_pct

ALERT_STEPS = [G, O, R]
S = 'testid=~"$testid", ep!~"setup|mailpit|reauth"'   # provisioning, Mailpit polling and token renewals are not user traffic

t = Board("nb-k6", "NextGen Bank - Performance tests (k6)", ["nextgen", "k6", "performance"], [
    {"name": "testid", "label": "Test run", "type": "query", "datasource": {"type": "prometheus", "uid": "prometheus"}, "includeAll": True,
     "multi": True, "allValue": ".+", "refresh": 2, "sort": 2, "query": {"query": "label_values(k6_vus, testid)", "refId": "v-testid"},
     "current": {"selected": True, "text": "All", "value": "$__all"}}])

t.row("Result of the selected run(s)")
t.stat("Peak VUs", "max(max_over_time(k6_vus{" + S + "}[$__range]))", 0, 3)
t.stat("Requests", "sum(max_over_time(k6_http_reqs_total{" + S + "}[$__range]))", 3, 3)
t.stat("Avg req/s", "sum(rate(k6_http_reqs_total{" + S + "}[$__range]))", 6, 3, unit="reqps", decimals=1)
t.stat("Error rate", "100 * (sum(increase(k6_http_reqs_total{" + S + ', expected_response="false"}[$__range])) or vector(0)) / sum(increase(k6_http_reqs_total{' + S + "}[$__range]))", 9, 3,
       unit="percent", decimals=2, steps=[G, {"color": "orange", "value": 1}, {"color": "red", "value": 5}], desc="Share of requests whose status the script did not expect.")
t.stat("Checks passed", "100 * avg(avg_over_time(k6_checks_rate{" + S + "}[$__range]))", 12, 3, unit="percent", decimals=2,
       steps=[{"color": "red", "value": None}, {"color": "orange", "value": 95}, {"color": "green", "value": 99}])
t.stat("p95 (worst endpoint)", "max(max_over_time(k6_http_req_duration_p95{" + S + "}[$__range]))", 15, 3, unit="ms", decimals=0, steps=[G, {"color": "orange", "value": 500}, {"color": "red", "value": 1000}])
t.stat("p99 (worst endpoint)", "max(max_over_time(k6_http_req_duration_p99{" + S + "}[$__range]))", 18, 3, unit="ms", decimals=0, steps=[G, {"color": "orange", "value": 1000}, {"color": "red", "value": 2000}])
t.stat("Iterations", "sum(max_over_time(k6_iterations_total{" + S + "}[$__range]))", 21, 3)
t.nxt(4)

t.row("Client side: what k6 measured")
t.ts("Virtual users", [t.tgt("max by (testid) (k6_vus{" + S + "})", "VUs {{testid}}")], 0, 8, 7)
t.ts("Requests / s", [t.tgt("sum by (testid) (rate(k6_http_reqs_total{" + S + "}[$__rate_interval]))", "{{testid}}")], 8, 8, 7, unit="reqps")
t.ts("Error rate %", [t.tgt("100 * (sum by (testid) (rate(k6_http_reqs_total{" + S + ', expected_response="false"}[$__rate_interval])) or (0 * sum by (testid) (rate(k6_http_reqs_total{' + S + "}[$__rate_interval])))) / sum by (testid) (rate(k6_http_reqs_total{" + S + "}[$__rate_interval]))", "{{testid}}")],
     16, 8, 7, unit="percent", minv=0, steps=[G, {"color": "red", "value": 5}])
t.nxt(7)
t.ts("Response time (avg / worst-endpoint percentiles)", [
    t.tgt("avg(k6_http_req_duration_avg{" + S + "})", "avg", "A"), t.tgt("max(k6_http_req_duration_p90{" + S + "})", "p90", "B"),
    t.tgt("max(k6_http_req_duration_p95{" + S + "})", "p95", "C"), t.tgt("max(k6_http_req_duration_p99{" + S + "})", "p99", "D"),
    t.tgt("max(k6_http_req_duration_max{" + S + "})", "max", "E")], 0, 12, 8, unit="ms")
t.ts("p95 by request", [t.tgt("max by (name) (k6_http_req_duration_p95{" + S + ', name!=""})', "{{name}}")], 12, 12, 8, unit="ms")
t.nxt(8)

t.row("Server side: what the platform experienced at the same time")
t.ts("API p95 latency (server)", [t.tgt('histogram_quantile(0.95, sum by (le) (rate(http_server_request_duration_seconds_bucket{service_name="nextgen-api"}[$__rate_interval])))', "api p95")], 0, 6, 7, unit="s")
t.ts("API 5xx / s", [t.tgt('sum(rate(http_server_request_duration_seconds_count{service_name="nextgen-api", http_response_status_code=~"5.."}[$__rate_interval]))', "5xx")], 6, 6, 7, unit="reqps", minv=0)
t.ts("Container CPU % of limit", [t.tgt(cpu_pct("api|celeryworker|postgres|pgbouncer|redis|rabbitmq"), "{{service}}")], 12, 12, 7, unit="percent", steps=ALERT_STEPS, minv=0)
t.nxt(7)
t.ts("PgBouncer: clients waiting / pool in use", [
    t.tgt("sum(pgbouncer_pools_client_waiting_connections)", "clients waiting", "A"),
    t.tgt("sum(pgbouncer_pools_server_active_connections)", "server connections active", "B")], 0, 6, 7)
t.ts("Postgres TPS", [t.tgt('sum(rate(pg_stat_database_xact_commit{job="postgres"}[$__rate_interval]) + rate(pg_stat_database_xact_rollback{job="postgres"}[$__rate_interval]))', "TPS")], 6, 6, 7, unit="ops")
t.ts("Redis commands / s and hit ratio", [
    t.tgt("rate(redis_commands_processed_total[$__rate_interval])", "commands/s", "A"),
    t.tgt("100 * rate(redis_keyspace_hits_total[$__rate_interval]) / (rate(redis_keyspace_hits_total[$__rate_interval]) + rate(redis_keyspace_misses_total[$__rate_interval]))", "hit ratio %", "B")], 12, 6, 7)
t.ts("RabbitMQ: ready / unacked", [t.tgt("sum(rabbitmq_queue_messages_ready)", "ready", "A"), t.tgt("sum(rabbitmq_queue_messages_unacked)", "unacked", "B")], 18, 6, 7, minv=0)
t.nxt(7)
t.save("dashboards/nb-k6.json", refresh="5s", frm="now-30m")
