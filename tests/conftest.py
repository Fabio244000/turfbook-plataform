from collections.abc import Callable, Generator
from uuid import uuid4

import pytest
from psycopg import Connection, connect, sql
from psycopg.rows import TupleRow

from config.settings import settings


def connect_as(user: str, password: str, dbname: str) -> Connection[TupleRow]:
    return connect(
        host=settings.master_db_host,
        port=settings.master_db_port,
        user=user,
        password=password,
        dbname=dbname,
        connect_timeout=settings.master_db_connect_timeout,
        autocommit=True,
    )


@pytest.fixture
def admin_connection() -> Generator[Connection[TupleRow], None, None]:
    with connect_as(
        settings.master_db_user, settings.master_db_password, settings.master_db_name
    ) as connection:
        yield connection


@pytest.fixture
def unique_name(
    admin_connection: Connection[TupleRow],
) -> Generator[Callable[[str], str], None, None]:
    """Returns unique names for databases and roles, and drops them after the test,
    so integration tests never collide or leave anything behind."""
    created: list[str] = []

    def make(prefix: str) -> str:
        name = f'{prefix}_{uuid4().hex[:8]}'
        created.append(name)
        return name

    yield make
    for name in created:
        identifier = sql.Identifier(name)
        admin_connection.execute(
            sql.SQL('DROP DATABASE IF EXISTS {}').format(identifier)
        )
    for name in created:
        identifier = sql.Identifier(name)
        admin_connection.execute(sql.SQL('DROP ROLE IF EXISTS {}').format(identifier))
