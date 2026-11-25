#!/bin/sh
# The CI runs this script before Postgres is ready, so it waits for it first.
set -eu

export PGHOST=localhost PGPORT=5432 PGUSER=turfbook PGPASSWORD=turfbook PGDATABASE=postgres

for _ in $(seq 60); do
  if pg_isready --quiet; then break; fi
  sleep 1
done
pg_isready

psql -v ON_ERROR_STOP=1 \
  -v admin_user="$MASTER_DB_USER" \
  -v admin_password="$MASTER_DB_PASSWORD" \
  -f scripts/database/create_local_admin.sql
