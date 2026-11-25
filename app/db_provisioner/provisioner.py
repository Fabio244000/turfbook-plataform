import re
from dataclasses import dataclass, field
from typing import Protocol

from app.db_provisioner import messages
from app.db_provisioner.exceptions import (
    DatabaseAlreadyProvisionedError,
    InvalidPayloadError,
    NotAuthorizedError,
    UserAlreadyExistsError,
)

# Lowercase PostgreSQL identifiers (max 63 bytes): no quoting surprises.
IDENTIFIER_PATTERN = re.compile(r'[a-z_][a-z0-9_]{0,62}')
# Letters and digits only, so the password is safe inside a DATABASE_URL.
PASSWORD_PATTERN = re.compile(r'[A-Za-z0-9]{15,}')
DROP_ACTION = 'drop'
# A drop only reaches the names a service deploy provisions:
# turfbook_<service>_<stage> owned by <service>_<stage>_db_user.
DROP_DB_PREFIX = 'turfbook_'
DROP_USERNAME_SUFFIX = '_db_user'


class DatabaseAdmin(Protocol):
    def database_exists(self, name: str) -> bool: ...

    def database_owner(self, name: str) -> str | None: ...

    def role_exists(self, name: str) -> bool: ...

    def create_role(self, name: str, password: str) -> None: ...

    def drop_role(self, name: str) -> None: ...

    def create_database(self, name: str, owner: str) -> None: ...

    def drop_database(self, name: str) -> None: ...


class LoginChecker(Protocol):
    def can_log_in(self, username: str, password: str, database: str | None) -> bool:
        """Whether `username` connects with `password` to `database` (None: the
        maintenance database, for a user whose database is gone)."""
        ...


@dataclass(frozen=True)
class ProvisionRequest:
    db_name: str
    username: str
    password: str = field(repr=False)

    @classmethod
    def from_event(cls, event: dict[str, object]) -> 'ProvisionRequest':
        db_name = _identifier(event, 'db_name')
        username = _identifier(event, 'username')
        return cls(db_name=db_name, username=username, password=_password(event))


@dataclass(frozen=True)
class DropRequest:
    db_name: str
    username: str
    password: str = field(repr=False)

    @classmethod
    def from_event(cls, event: dict[str, object]) -> 'DropRequest':
        db_name = _identifier(event, 'db_name')
        if not db_name.startswith(DROP_DB_PREFIX):
            raise InvalidPayloadError(
                messages.DROP_DB_NAME_RULE.format(prefix=DROP_DB_PREFIX)
            )
        username = _identifier(event, 'username')
        if not username.endswith(DROP_USERNAME_SUFFIX):
            raise InvalidPayloadError(
                messages.DROP_USERNAME_RULE.format(suffix=DROP_USERNAME_SUFFIX)
            )
        return cls(db_name=db_name, username=username, password=_password(event))


def _identifier(event: dict[str, object], key: str) -> str:
    value = event.get(key)
    if not isinstance(value, str) or not IDENTIFIER_PATTERN.fullmatch(value):
        raise InvalidPayloadError(
            messages.IDENTIFIER_RULE.format(key=key, pattern=IDENTIFIER_PATTERN.pattern)
        )
    return value


def _password(event: dict[str, object]) -> str:
    password = event.get('password')
    if not isinstance(password, str) or not PASSWORD_PATTERN.fullmatch(password):
        raise InvalidPayloadError(messages.PASSWORD_RULE)
    return password


def parse_request(event: dict[str, object]) -> ProvisionRequest | DropRequest:
    """No `action` creates (the original contract); `drop` drops."""
    if 'action' not in event:
        return ProvisionRequest.from_event(event)
    if event['action'] != DROP_ACTION:
        raise InvalidPayloadError(messages.UNKNOWN_ACTION)
    return DropRequest.from_event(event)


def execute(
    request: ProvisionRequest | DropRequest,
    admin: DatabaseAdmin,
    logins: LoginChecker,
) -> dict[str, str]:
    if isinstance(request, DropRequest):
        return drop(request, admin, logins)
    return provision(request, admin)


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


def drop(
    request: DropRequest, admin: DatabaseAdmin, logins: LoginChecker
) -> dict[str, str]:
    """Drops the database and its user, only for whoever proves to own them.
    Idempotent: a retry finishes a drop that failed halfway (the user left)."""
    owner = admin.database_owner(request.db_name)
    if owner is None and not admin.role_exists(request.username):
        return {'status': 'absent'}
    _authorize(request, owner, logins)
    if owner is not None:
        admin.drop_database(request.db_name)
    admin.drop_role(request.username)
    return {'status': 'dropped'}


def _authorize(request: DropRequest, owner: str | None, logins: LoginChecker) -> None:
    """With its database, the user must own it and connect to it; without it, the
    user must connect to the maintenance database."""
    database = None if owner is None else request.db_name
    owns = owner is None or owner == request.username
    if not owns or not logins.can_log_in(request.username, request.password, database):
        raise NotAuthorizedError(request.db_name, request.username)
