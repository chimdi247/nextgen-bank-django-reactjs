#!/bin/bash
# Hot-standby replica: on first start, clones the primary with pg_basebackup (streaming, using the replication slot
# created by init/00-replication.sh), then runs as a read-only standby. Feeds the "Replication lag" panels.
set -euo pipefail

PRIMARY_HOST="${PRIMARY_HOST:-postgres}"
export PGDATA="${PGDATA:-/var/lib/postgresql/data}"

if [ ! -s "$PGDATA/PG_VERSION" ]; then
  echo "replica: waiting for the primary at ${PRIMARY_HOST}..."
  until pg_isready -h "$PRIMARY_HOST" -p 5432 -U "$POSTGRES_USER" >/dev/null 2>&1; do sleep 2; done

  mkdir -p "$PGDATA"
  chown -R postgres:postgres "$PGDATA"
  chmod 700 "$PGDATA"

  echo "replica: taking a base backup"
  gosu postgres env PGPASSWORD="${REPLICATION_PASSWORD}" \
    pg_basebackup -h "$PRIMARY_HOST" -p 5432 -U replicator -D "$PGDATA" -Fp -Xs -R -S replica_slot -P
fi

exec docker-entrypoint.sh postgres -c hot_standby=on -c max_connections=100
