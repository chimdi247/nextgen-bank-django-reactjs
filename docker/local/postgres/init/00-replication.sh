#!/bin/bash
# Runs once, on first initialisation of the primary: creates the replication role + slot and lets the replica connect.
# (Streaming replication feeds the "Replication lag" panels in Grafana.)
set -e
: "${REPLICATION_PASSWORD:?REPLICATION_PASSWORD must be set in .envs/.env.local}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<SQL
CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD '${REPLICATION_PASSWORD}';
SELECT pg_create_physical_replication_slot('replica_slot');
SQL

# the default pg_hba.conf of the image has no rule for the pseudo-database "replication" from other hosts
echo "host replication replicator all scram-sha-256" >> "$PGDATA/pg_hba.conf"
