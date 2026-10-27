from psycopg import Connection, sql
from psycopg.rows import TupleRow

CONNECTION_LIMIT = 20


class PostgresDatabaseAdmin:
    """DatabaseAdmin adapter. Needs an autocommit connection (CREATE DATABASE cannot
    run inside a transaction) of a role with CREATEROLE and CREATEDB, like the RDS
    master user. Identifiers and the password are composed with psycopg.sql, never
    by concatenating text."""

    def __init__(self, connection: Connection[TupleRow]) -> None:
        self._connection = connection

    def database_exists(self, name: str) -> bool:
        return self._exists('SELECT 1 FROM pg_database WHERE datname = %s', name)

    def role_exists(self, name: str) -> bool:
        return self._exists('SELECT 1 FROM pg_roles WHERE rolname = %s', name)

    def create_role(self, name: str, password: str) -> None:
        role = sql.Identifier(name)
        self._execute(
            sql.SQL('CREATE ROLE {} LOGIN PASSWORD {} CONNECTION LIMIT {}').format(
                role, sql.Literal(password), sql.Literal(CONNECTION_LIMIT)
            )
        )
        # PostgreSQL 16: to make another role the owner of a new database, the admin
        # must be able to SET ROLE to it.
        self._execute(sql.SQL('GRANT {} TO CURRENT_USER').format(role))

    def drop_role(self, name: str) -> None:
        self._execute(sql.SQL('DROP ROLE IF EXISTS {}').format(sql.Identifier(name)))

    def create_database(self, name: str, owner: str) -> None:
        database, role = sql.Identifier(name), sql.Identifier(owner)
        self._execute(sql.SQL('CREATE DATABASE {} OWNER {}').format(database, role))
        self._execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(database))
        self._execute(
            sql.SQL('GRANT CONNECT ON DATABASE {} TO {}').format(database, role)
        )

    def _exists(self, query: str, name: str) -> bool:
        return self._connection.execute(query, (name,)).fetchone() is not None

    def _execute(self, statement: sql.Composed) -> None:
        self._connection.execute(statement)
