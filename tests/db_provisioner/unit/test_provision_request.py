import pytest

from app.db_provisioner.exceptions import InvalidPayloadError
from app.db_provisioner.provisioner import ProvisionRequest

PASSWORD = 'Abc123def456Ghi'


def _event(**overrides: object) -> dict[str, object]:
    event: dict[str, object] = {
        'db_name': 'turfbook_identity_dev',
        'username': 'identity_dev_db_user',
        'password': PASSWORD,
    }
    event.update(overrides)
    return event


class TestProvisionRequest:
    def test_builds_from_a_valid_event(self) -> None:
        request = ProvisionRequest.from_event(_event())

        assert request == ProvisionRequest(
            'turfbook_identity_dev', 'identity_dev_db_user', PASSWORD
        )

    @pytest.mark.parametrize('key', ['db_name', 'username', 'password'])
    def test_rejects_a_missing_field(self, key: str) -> None:
        event = _event()
        del event[key]

        with pytest.raises(InvalidPayloadError):
            ProvisionRequest.from_event(event)

    @pytest.mark.parametrize(
        'name',
        [
            'Identity',
            '1identity',
            'identity-dev',
            'x; DROP ROLE postgres',
            '',
            'a' * 64,
        ],
    )
    @pytest.mark.parametrize('key', ['db_name', 'username'])
    def test_rejects_names_that_are_not_lowercase_identifiers(
        self, key: str, name: str
    ) -> None:
        with pytest.raises(InvalidPayloadError, match=key):
            ProvisionRequest.from_event(_event(**{key: name}))

    @pytest.mark.parametrize(
        'password', ['Abc123', 'Abc123def456Gh!', 'Abc 123 def 456']
    )
    def test_rejects_a_password_that_breaks_the_rules(self, password: str) -> None:
        with pytest.raises(InvalidPayloadError, match='password') as raised:
            ProvisionRequest.from_event(_event(password=password))

        assert password not in str(raised.value)

    @pytest.mark.parametrize('password', [123456789012345, None])
    def test_rejects_a_password_that_is_not_text(self, password: object) -> None:
        with pytest.raises(InvalidPayloadError, match='password'):
            ProvisionRequest.from_event(_event(password=password))

    def test_never_shows_the_password_in_its_repr(self) -> None:
        request = ProvisionRequest.from_event(_event())

        assert PASSWORD not in repr(request)
