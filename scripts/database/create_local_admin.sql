-- Local and CI only: an admin with the same privileges as the RDS master user
-- (CREATEROLE and CREATEDB, not superuser), so tests exercise what the db-provisioner
-- can really do in AWS. Run as the container superuser:
--   psql -v ON_ERROR_STOP=1 -v admin_user=<user> -v admin_password=<password> \
--        -f create_local_admin.sql
CREATE ROLE :"admin_user" LOGIN PASSWORD :'admin_password' CREATEROLE CREATEDB;
