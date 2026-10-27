from collections.abc import Callable

import pytest
from psycopg import Connection, OperationalError
from psycopg.rows import TupleRow

from app.db_provisioner.exceptions import (
    DatabaseAlreadyProvisionedError,
    UserAlreadyExistsError,
)
from app.db_provisioner.postgres_admin import PostgresDatabaseAdmin
from app.db_provisioner.provisioner import ProvisionRequest, provision
from tests.conftest import connect_as

PASSWORD = 'Abc123def456Ghi'
OTHER_PASSWORD = 'Xyz789uvw012Rst'

NameFactory = Callable[[str], str]


def _provision(
    connection: Connection[TupleRow], db_name: str, username: str, password: str
) -> dict[str, str]:
    request = ProvisionRequest(db_name, username, password)
    return provision(request, PostgresDatabaseAdmin(connection))


class TestPostgresProvisioning:
    def test_the_new_user_can_connect_to_its_database(
        self, admin_connection: Connection[TupleRow], unique_name: NameFactory
    ) -> None:
        db_name, username = unique_name('db'), unique_name('user')

        result = _provision(admin_connection, db_name, username, PASSWORD)

        assert result == {'status': 'created'}
        with connect_as(username, PASSWORD, db_name) as connection:
            row = connection.execute('SELECT current_database()').fetchone()
        assert row == (db_name,)

    def test_the_new_user_owns_its_database(
        self, admin_connection: Connection[TupleRow], unique_name: NameFactory
    ) -> None:
        db_name, username = unique_name('db'), unique_name('user')

        _provision(admin_connection, db_name, username, PASSWORD)

        owner = admin_connection.execute(
            'SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = %s',
            (db_name,),
        ).fetchone()
        assert owner == (username,)

    def test_a_user_cannot_connect_to_another_service_database(
        self, admin_connection: Connection[TupleRow], unique_name: NameFactory
    ) -> None:
        identity_db, identity_user = unique_name('db'), unique_name('user')
        owner_db, owner_user = unique_name('db'), unique_name('user')
        _provision(admin_connection, identity_db, identity_user, PASSWORD)
        _provision(admin_connection, owner_db, owner_user, OTHER_PASSWORD)

        with pytest.raises(OperationalError, match='permission denied'):
            connect_as(owner_user, OTHER_PASSWORD, identity_db)

    def test_fails_when_the_database_is_already_provisioned(
        self, admin_connection: Connection[TupleRow], unique_name: NameFactory
    ) -> None:
        db_name, username = unique_name('db'), unique_name('user')
        _provision(admin_connection, db_name, username, PASSWORD)

        with pytest.raises(DatabaseAlreadyProvisionedError):
            _provision(admin_connection, db_name, unique_name('user'), PASSWORD)

    def test_fails_when_the_user_already_exists(
        self, admin_connection: Connection[TupleRow], unique_name: NameFactory
    ) -> None:
        username = unique_name('user')
        _provision(admin_connection, unique_name('db'), username, PASSWORD)

        with pytest.raises(UserAlreadyExistsError):
            _provision(admin_connection, unique_name('db'), username, PASSWORD)
