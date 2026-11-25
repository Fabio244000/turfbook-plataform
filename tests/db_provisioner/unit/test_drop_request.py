import pytest

from app.db_provisioner.exceptions import InvalidPayloadError
from app.db_provisioner.provisioner import DropRequest

PASSWORD = 'Abc123def456Ghi'


def _event(**overrides: object) -> dict[str, object]:
    event: dict[str, object] = {
        'action': 'drop',
        'db_name': 'turfbook_identity_dev',
        'username': 'identity_dev_db_user',
        'password': PASSWORD,
    }
    event.update(overrides)
    return event


class TestDropRequest:
    def test_builds_from_a_valid_event(self) -> None:
        request = DropRequest.from_event(_event())

        assert request == DropRequest(
            'turfbook_identity_dev', 'identity_dev_db_user', PASSWORD
        )

    @pytest.mark.parametrize('key', ['db_name', 'username', 'password'])
    def test_rejects_a_missing_field(self, key: str) -> None:
        event = _event()
        del event[key]

        with pytest.raises(InvalidPayloadError, match=key):
            DropRequest.from_event(event)

    @pytest.mark.parametrize(
        'db_name', ['identity_dev', 'xturfbook_identity_dev', 'turfbookidentity']
    )
    def test_rejects_a_database_outside_turfbook(self, db_name: str) -> None:
        with pytest.raises(InvalidPayloadError, match='db_name'):
            DropRequest.from_event(_event(db_name=db_name))

    @pytest.mark.parametrize(
        'username', ['identity_dev_user', 'identity_db_user_dev', 'identitydb_user']
    )
    def test_rejects_a_user_outside_db_user(self, username: str) -> None:
        with pytest.raises(InvalidPayloadError, match='username'):
            DropRequest.from_event(_event(username=username))

    @pytest.mark.parametrize(
        ('key', 'name'),
        [
            ('db_name', 'turfbook-identity-dev'),
            ('db_name', 'Turfbook_identity_dev'),
            ('username', 'identity-dev_db_user'),
            ('username', 'x; DROP ROLE postgres; --_db_user'),
        ],
    )
    def test_rejects_names_that_are_not_lowercase_identifiers(
        self, key: str, name: str
    ) -> None:
        with pytest.raises(InvalidPayloadError, match=key):
            DropRequest.from_event(_event(**{key: name}))

    @pytest.mark.parametrize('password', ['Abc123', 'Abc123def456Gh!'])
    def test_rejects_a_password_that_breaks_the_rules(self, password: str) -> None:
        with pytest.raises(InvalidPayloadError, match='password') as raised:
            DropRequest.from_event(_event(password=password))

        assert password not in str(raised.value)

    def test_never_shows_the_password_in_its_repr(self) -> None:
        request = DropRequest.from_event(_event())

        assert PASSWORD not in repr(request)
