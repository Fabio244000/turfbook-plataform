import re
from dataclasses import dataclass, field
from typing import Protocol

from app.db_provisioner.exceptions import (
    DatabaseAlreadyProvisionedError,
    InvalidPayloadError,
    UserAlreadyExistsError,
)

# Lowercase PostgreSQL identifiers (max 63 bytes): no quoting surprises.
IDENTIFIER_PATTERN = re.compile(r'[a-z_][a-z0-9_]{0,62}')
# Letters and digits only, so the password is safe inside a DATABASE_URL.
PASSWORD_PATTERN = re.compile(r'[A-Za-z0-9]{15,}')
PASSWORD_RULE = 'password must have at least 15 characters, letters and digits only'


class DatabaseAdmin(Protocol):
    def database_exists(self, name: str) -> bool: ...

    def role_exists(self, name: str) -> bool: ...

    def create_role(self, name: str, password: str) -> None: ...

    def drop_role(self, name: str) -> None: ...

    def create_database(self, name: str, owner: str) -> None: ...


@dataclass(frozen=True)
class ProvisionRequest:
    db_name: str
    username: str
    password: str = field(repr=False)

    @classmethod
    def from_event(cls, event: dict[str, object]) -> 'ProvisionRequest':
        db_name = _identifier(event, 'db_name')
        username = _identifier(event, 'username')
        password = event.get('password')
        if not isinstance(password, str) or not PASSWORD_PATTERN.fullmatch(password):
            raise InvalidPayloadError(PASSWORD_RULE)
        return cls(db_name=db_name, username=username, password=password)


def _identifier(event: dict[str, object], key: str) -> str:
    value = event.get(key)
    if not isinstance(value, str) or not IDENTIFIER_PATTERN.fullmatch(value):
        raise InvalidPayloadError(
            f'{key} must be a lowercase identifier ({IDENTIFIER_PATTERN.pattern})'
        )
    return value


def provision(request: ProvisionRequest, admin: DatabaseAdmin) -> dict[str, str]:
    """Creates the login role and its database. Success only when both are created:
    an existing database or role is an error, never something to reuse."""
    if admin.database_exists(request.db_name):
        raise DatabaseAlreadyProvisionedError(request.db_name)
    if admin.role_exists(request.username):
        raise UserAlreadyExistsError(request.username)
    admin.create_role(request.username, request.password)
    try:
        admin.create_database(request.db_name, owner=request.username)
    except Exception:
        # Leave nothing half-done, so a retry does not hit UserAlreadyExistsError.
        admin.drop_role(request.username)
        raise
    return {'status': 'created'}
