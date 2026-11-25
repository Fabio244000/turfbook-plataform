import pytest

from app.db_provisioner.exceptions import InvalidPayloadError
from app.db_provisioner.provisioner import (
    DropRequest,
    ProvisionRequest,
    execute,
    parse_request,
)
from tests.fakes.database_admin import FakeDatabaseAdmin

DB_NAME = 'turfbook_identity_dev'
USERNAME = 'identity_dev_db_user'
PASSWORD = 'Abc123def456Ghi'


def _event(**overrides: object) -> dict[str, object]:
    event: dict[str, object] = {
        'db_name': DB_NAME,
        'username': USERNAME,
        'password': PASSWORD,
    }
    event.update(overrides)
    return event


class TestParseRequest:
    def test_an_event_without_action_creates(self) -> None:
        request = parse_request(_event())

        assert request == ProvisionRequest(DB_NAME, USERNAME, PASSWORD)

    def test_the_drop_action_drops(self) -> None:
        request = parse_request(_event(action='drop'))

        assert request == DropRequest(DB_NAME, USERNAME, PASSWORD)

    @pytest.mark.parametrize('action', ['delete', 'create', 'DROP', '', None, 1])
    def test_rejects_an_unknown_action(self, action: object) -> None:
        with pytest.raises(InvalidPayloadError, match='action'):
            parse_request(_event(action=action))


class TestExecute:
    def test_a_provision_request_creates(self) -> None:
        admin = FakeDatabaseAdmin()

        result = execute(ProvisionRequest(DB_NAME, USERNAME, PASSWORD), admin, admin)

        assert result == {'status': 'created'}
        assert admin.databases == {DB_NAME: USERNAME}

    def test_a_drop_request_drops(self) -> None:
        admin = FakeDatabaseAdmin(
            databases={DB_NAME: USERNAME}, roles={USERNAME: PASSWORD}
        )

        result = execute(DropRequest(DB_NAME, USERNAME, PASSWORD), admin, admin)

        assert result == {'status': 'dropped'}
        assert admin.databases == {}
