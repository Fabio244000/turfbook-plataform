import logging
from collections.abc import Callable

import pytest

from app.db_provisioner.exceptions import InvalidPayloadError, NotAuthorizedError
from app.db_provisioner.handler import handler

PASSWORD = 'Abc123def456Ghi'
OTHER_PASSWORD = 'Xyz789uvw012Rst'

NameFactory = Callable[..., str]


def _event(db_name: str, username: str, **overrides: object) -> dict[str, object]:
    event: dict[str, object] = {
        'db_name': db_name,
        'username': username,
        'password': PASSWORD,
    }
    event.update(overrides)
    return event


@pytest.fixture
def names(unique_name: NameFactory) -> tuple[str, str]:
    return unique_name('turfbook'), unique_name('user', '_db_user')


class TestHandler:
    def test_creates_then_drops_a_service_database(
        self, names: tuple[str, str]
    ) -> None:
        created = handler(_event(*names), None)
        dropped = handler(_event(*names, action='drop'), None)
        absent = handler(_event(*names, action='drop'), None)

        assert (created, dropped, absent) == (
            {'status': 'created'},
            {'status': 'dropped'},
            {'status': 'absent'},
        )

    def test_refuses_a_drop_with_another_password(self, names: tuple[str, str]) -> None:
        handler(_event(*names), None)

        with pytest.raises(NotAuthorizedError):
            handler(_event(*names, action='drop', password=OTHER_PASSWORD), None)

    def test_rejects_an_invalid_event_before_connecting(self) -> None:
        with pytest.raises(InvalidPayloadError):
            handler({}, None)

    def test_never_logs_the_password(
        self, names: tuple[str, str], caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.INFO)

        handler(_event(*names), None)
        handler(_event(*names, action='drop'), None)

        assert names[0] in caplog.text
        assert PASSWORD not in caplog.text
