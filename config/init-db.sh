#!/bin/sh
set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set=runtime_password="$DB_RUNTIME_PASSWORD" <<'SQL'
CREATE ROLE meeting_runtime LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD :'runtime_password';
GRANT CONNECT ON DATABASE meeting TO meeting_runtime;
GRANT USAGE ON SCHEMA public TO meeting_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE meeting_owner IN SCHEMA public GRANT SELECT,INSERT,UPDATE,DELETE ON TABLES TO meeting_runtime;
SQL

