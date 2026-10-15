#!/bin/bash
# Renders pgbouncer.ini + userlist.txt from environment variables, then runs pgbouncer in the foreground.
#
# Transaction pooling: a server connection is held only for the length of a transaction, so a few dozen Postgres
# connections serve hundreds of Django / Celery connections. The pool sizes below are what the "PgBouncer" Grafana
# dashboard measures (pool usage % = server connections in use / DEFAULT_POOL_SIZE).
set -euo pipefail

: "${POSTGRES_USER:?}" "${POSTGRES_PASSWORD:?}" "${POSTGRES_DB:?}"

cat > /etc/pgbouncer/pgbouncer.ini <<INI
[databases]
${POSTGRES_DB} = host=${PGBOUNCER_BACKEND_HOST:-postgres} port=${PGBOUNCER_BACKEND_PORT:-5432} dbname=${POSTGRES_DB}
; the exporter / admins connect to the virtual "pgbouncer" database (SHOW POOLS, SHOW STATS ...)

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
unix_socket_dir = /var/run/pgbouncer
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = ${PGBOUNCER_POOL_MODE:-transaction}
max_client_conn = ${PGBOUNCER_MAX_CLIENT_CONN:-300}
default_pool_size = ${PGBOUNCER_DEFAULT_POOL_SIZE:-20}
reserve_pool_size = ${PGBOUNCER_RESERVE_POOL_SIZE:-5}
reserve_pool_timeout = 3
server_idle_timeout = 300
query_wait_timeout = 30
admin_users = ${POSTGRES_USER}
stats_users = ${POSTGRES_USER}
ignore_startup_parameters = extra_float_digits,options
log_connections = 0
log_disconnections = 0
log_pooler_errors = 1
stats_period = 15
INI

# plain-text password: pgbouncer derives the SCRAM proof from it (so it also works against scram-sha-256 servers)
printf '"%s" "%s"\n' "${POSTGRES_USER}" "${POSTGRES_PASSWORD}" > /etc/pgbouncer/userlist.txt
chmod 600 /etc/pgbouncer/userlist.txt

exec pgbouncer /etc/pgbouncer/pgbouncer.ini
