from collections.abc import Callable

import pytest
from psycopg import Connection, OperationalError
from psycopg.rows import TupleRow

from app.db_provisioner.postgres_admin import (
    PostgresDatabaseAdmin,
    PostgresLoginChecker,
)
from app.db_provisioner.provisioner import (
    DropRequest,
    ProvisionRequest,
    drop,
    provision,
)
from config.settings import settings
from tests.conftest import connect_as

PASSWORD = 'Abc123def456Ghi'
OTHER_PASSWORD = 'Xyz789uvw012Rst'

NameFactory = Callable[[str], str]


@pytest.fixture
def admin(admin_connection: Connection[TupleRow]) -> PostgresDatabaseAdmin:
    return PostgresDatabaseAdmin(admin_connection)


@pytest.fixture
def logins() -> PostgresLoginChecker:
    return PostgresLoginChecker(
        host=settings.master_db_host,
        port=settings.master_db_port,
        connect_timeout=settings.master_db_connect_timeout,
        maintenance_db=settings.master_db_name,
    )


@pytest.fixture
def provisioned(
    admin: PostgresDatabaseAdmin, unique_name: NameFactory
) -> tuple[str, str]:
    db_name, username = unique_name('db'), unique_name('user')
    provision(ProvisionRequest(db_name, username, PASSWORD), admin)
    return db_name, username


class TestPostgresDatabaseAdmin:
    def test_reads_the_owner_of_a_database(
        self, admin: PostgresDatabaseAdmin, provisioned: tuple[str, str]
    ) -> None:
        db_name, username = provisioned

        assert admin.database_owner(db_name) == username

    def test_a_missing_database_has_no_owner(
        self, admin: PostgresDatabaseAdmin, unique_name: NameFactory
    ) -> None:
        assert admin.database_owner(unique_name('db')) is None

    def test_drops_a_database_its_owner_is_connected_to(
        self, admin: PostgresDatabaseAdmin, provisioned: tuple[str, str]
    ) -> None:
        db_name, username = provisioned

        with connect_as(username, PASSWORD, db_name):
            admin.drop_database(db_name)

        assert not admin.database_exists(db_name)


class TestPostgresLoginChecker:
    def test_the_owner_connects_to_its_database(
        self, logins: PostgresLoginChecker, provisioned: tuple[str, str]
    ) -> None:
        db_name, username = provisioned

        assert logins.can_log_in(username, PASSWORD, db_name)

    def test_a_wrong_password_does_not_connect(
        self, logins: PostgresLoginChecker, provisioned: tuple[str, str]
    ) -> None:
        db_name, username = provisioned

        assert not logins.can_log_in(username, OTHER_PASSWORD, db_name)

    def test_a_user_does_not_connect_to_another_service_database(
        self,
        admin: PostgresDatabaseAdmin,
        logins: PostgresLoginChecker,
        provisioned: tuple[str, str],
        unique_name: NameFactory,
    ) -> None:
        db_name, _ = provisioned
        other_username = unique_name('user')
        provision(
            ProvisionRequest(unique_name('db'), other_username, OTHER_PASSWORD), admin
        )

        assert not logins.can_log_in(other_username, OTHER_PASSWORD, db_name)

    def test_a_user_without_its_database_connects_to_the_maintenance_database(
        self,
        admin: PostgresDatabaseAdmin,
        logins: PostgresLoginChecker,
        provisioned: tuple[str, str],
    ) -> None:
        db_name, username = provisioned
        admin.drop_database(db_name)

        assert logins.can_log_in(username, PASSWORD, None)


class TestPostgresDrop:
    def test_drops_the_database_and_its_user(
        self,
        admin: PostgresDatabaseAdmin,
        logins: PostgresLoginChecker,
        provisioned: tuple[str, str],
    ) -> None:
        db_name, username = provisioned

        result = drop(DropRequest(db_name, username, PASSWORD), admin, logins)

        assert result == {'status': 'dropped'}
        assert not admin.database_exists(db_name)
        assert not admin.role_exists(username)
        with pytest.raises(OperationalError):
            connect_as(username, PASSWORD, settings.master_db_name)
