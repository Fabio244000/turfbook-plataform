import pytest

from app.db_provisioner.exceptions import (
    DatabaseAlreadyProvisionedError,
    UserAlreadyExistsError,
)
from app.db_provisioner.provisioner import ProvisionRequest, provision
from tests.fakes.database_admin import FakeDatabaseAdmin

DB_NAME = 'turfbook_identity_dev'
USERNAME = 'identity_dev_db_user'
PASSWORD = 'Abc123def456Ghi'
REQUEST = ProvisionRequest(DB_NAME, USERNAME, PASSWORD)


class TestProvision:
    def test_creates_the_role_and_its_database(self) -> None:
        admin = FakeDatabaseAdmin()

        result = provision(REQUEST, admin)

        assert result == {'status': 'created'}
        assert admin.roles == {USERNAME: PASSWORD}
        assert admin.owners == {DB_NAME: USERNAME}

    def test_fails_when_the_database_is_already_provisioned(self) -> None:
        admin = FakeDatabaseAdmin(databases={DB_NAME})

        with pytest.raises(DatabaseAlreadyProvisionedError, match=DB_NAME):
            provision(REQUEST, admin)

        assert admin.roles == {}

    def test_checks_the_database_before_the_user(self) -> None:
        admin = FakeDatabaseAdmin(databases={DB_NAME}, roles={USERNAME})

        with pytest.raises(DatabaseAlreadyProvisionedError):
            provision(REQUEST, admin)

    def test_fails_when_the_user_already_exists(self) -> None:
        admin = FakeDatabaseAdmin(roles={USERNAME})

        with pytest.raises(UserAlreadyExistsError, match=USERNAME):
            provision(REQUEST, admin)

        assert admin.databases == set()

    def test_drops_the_new_role_when_the_database_cannot_be_created(self) -> None:
        admin = FakeDatabaseAdmin(create_database_error=RuntimeError('disk full'))

        with pytest.raises(RuntimeError, match='disk full'):
            provision(REQUEST, admin)

        assert admin.roles == {}
