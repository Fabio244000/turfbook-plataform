import pytest

from app.db_provisioner.exceptions import NotAuthorizedError
from app.db_provisioner.provisioner import DropRequest, drop
from tests.fakes.database_admin import FakeDatabaseAdmin

DB_NAME = 'turfbook_identity_dev'
USERNAME = 'identity_dev_db_user'
PASSWORD = 'Abc123def456Ghi'
OTHER_DB_NAME = 'turfbook_owner_dev'
OTHER_USERNAME = 'owner_dev_db_user'
OTHER_PASSWORD = 'Xyz789uvw012Rst'
REQUEST = DropRequest(DB_NAME, USERNAME, PASSWORD)


def _provisioned_admin() -> FakeDatabaseAdmin:
    """Two services provisioned: the one dropped and another that must stay intact."""
    return FakeDatabaseAdmin(
        databases={DB_NAME: USERNAME, OTHER_DB_NAME: OTHER_USERNAME},
        roles={USERNAME: PASSWORD, OTHER_USERNAME: OTHER_PASSWORD},
    )


def _drop(request: DropRequest, admin: FakeDatabaseAdmin) -> dict[str, str]:
    return drop(request, admin, admin)


class TestDrop:
    def test_drops_the_database_and_its_user(self) -> None:
        admin = _provisioned_admin()

        result = _drop(REQUEST, admin)

        assert result == {'status': 'dropped'}
        assert DB_NAME not in admin.databases
        assert USERNAME not in admin.roles

    def test_leaves_other_services_untouched(self) -> None:
        admin = _provisioned_admin()

        _drop(REQUEST, admin)

        assert admin.databases == {OTHER_DB_NAME: OTHER_USERNAME}
        assert admin.roles == {OTHER_USERNAME: OTHER_PASSWORD}

    def test_a_second_drop_answers_absent(self) -> None:
        admin = _provisioned_admin()
        _drop(REQUEST, admin)

        result = _drop(REQUEST, admin)

        assert result == {'status': 'absent'}

    def test_answers_absent_when_nothing_exists(self) -> None:
        admin = FakeDatabaseAdmin()

        result = _drop(REQUEST, admin)

        assert result == {'status': 'absent'}

    def test_drops_the_user_left_when_its_database_is_gone(self) -> None:
        admin = FakeDatabaseAdmin(roles={USERNAME: PASSWORD})

        result = _drop(REQUEST, admin)

        assert result == {'status': 'dropped'}
        assert admin.roles == {}


class TestDropAuthorization:
    def test_refuses_a_wrong_password(self) -> None:
        admin = _provisioned_admin()
        request = DropRequest(DB_NAME, USERNAME, OTHER_PASSWORD)

        with pytest.raises(NotAuthorizedError, match=DB_NAME):
            _drop(request, admin)

        assert admin.databases[DB_NAME] == USERNAME
        assert USERNAME in admin.roles

    def test_refuses_a_user_that_does_not_exist(self) -> None:
        admin = _provisioned_admin()
        request = DropRequest(DB_NAME, 'nobody_dev_db_user', PASSWORD)

        with pytest.raises(NotAuthorizedError, match=DB_NAME):
            _drop(request, admin)

        assert admin.databases[DB_NAME] == USERNAME

    def test_refuses_another_service_user_with_its_own_password(self) -> None:
        admin = _provisioned_admin()
        request = DropRequest(DB_NAME, OTHER_USERNAME, OTHER_PASSWORD)

        with pytest.raises(NotAuthorizedError, match=DB_NAME):
            _drop(request, admin)

        assert admin.databases[DB_NAME] == USERNAME
        assert OTHER_USERNAME in admin.roles

    def test_refuses_a_wrong_password_when_only_the_user_is_left(self) -> None:
        admin = FakeDatabaseAdmin(roles={USERNAME: PASSWORD})
        request = DropRequest(DB_NAME, USERNAME, OTHER_PASSWORD)

        with pytest.raises(NotAuthorizedError, match=USERNAME):
            _drop(request, admin)

        assert USERNAME in admin.roles

    def test_never_shows_the_password_in_the_error(self) -> None:
        admin = _provisioned_admin()
        request = DropRequest(DB_NAME, USERNAME, OTHER_PASSWORD)

        with pytest.raises(NotAuthorizedError) as raised:
            _drop(request, admin)

        assert OTHER_PASSWORD not in str(raised.value)
