from psycopg import Connection, OperationalError, connect, sql
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

    def database_owner(self, name: str) -> str | None:
        row = self._connection.execute(
            'SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = %s',
            (name,),
        ).fetchone()
        return None if row is None else str(row[0])

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

    def drop_database(self, name: str) -> None:
        # FORCE closes the connections to it first (the admin holds the owner's
        # privileges through the GRANT of create_role, so it may terminate them).
        self._execute(
            sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(
                sql.Identifier(name)
            )
        )

    def _exists(self, query: str, name: str) -> bool:
        return self._connection.execute(query, (name,)).fetchone() is not None

    def _execute(self, statement: sql.Composed) -> None:
        self._connection.execute(statement)


class PostgresLoginChecker:
    """LoginChecker adapter: opens and closes one short connection as the user. Any
    failure to connect (wrong password, no CONNECT on the database, its connection
    limit) means it cannot log in."""

    def __init__(
        self, host: str, port: int, connect_timeout: int, maintenance_db: str
    ) -> None:
        self._host = host
        self._port = port
        self._connect_timeout = connect_timeout
        self._maintenance_db = maintenance_db

    def can_log_in(self, username: str, password: str, database: str | None) -> bool:
        try:
            with connect(
                host=self._host,
                port=self._port,
                user=username,
                password=password,
                dbname=database or self._maintenance_db,
                connect_timeout=self._connect_timeout,
            ):
                return True
        except OperationalError:
            return False
