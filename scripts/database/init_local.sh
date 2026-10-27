#!/bin/sh
# Local only: run by the Postgres container on its first start (empty volume).
set -eu

psql -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  -v admin_user="$MASTER_DB_USER" \
  -v admin_password="$MASTER_DB_PASSWORD" \
  -f /sql/create_local_admin.sql
