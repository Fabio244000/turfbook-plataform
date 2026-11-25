class FakeDatabaseAdmin:
    """In-memory DatabaseAdmin and LoginChecker. `databases` maps each database to its
    owner and `roles` each role to its password. Like the real databases, only the owner
    can connect to a database (CONNECT is revoked from PUBLIC)."""

    def __init__(
        self,
        databases: dict[str, str] | None = None,
        roles: dict[str, str] | None = None,
        create_database_error: Exception | None = None,
    ) -> None:
        self.databases: dict[str, str] = dict(databases or {})
        self.roles: dict[str, str] = dict(roles or {})
        self._create_database_error = create_database_error

    def database_exists(self, name: str) -> bool:
        return name in self.databases

    def database_owner(self, name: str) -> str | None:
        return self.databases.get(name)

    def role_exists(self, name: str) -> bool:
        return name in self.roles

    def create_role(self, name: str, password: str) -> None:
        self.roles[name] = password

    def drop_role(self, name: str) -> None:
        self.roles.pop(name, None)

    def create_database(self, name: str, owner: str) -> None:
        if self._create_database_error is not None:
            raise self._create_database_error
        self.databases[name] = owner

    def drop_database(self, name: str) -> None:
        self.databases.pop(name, None)

    def can_log_in(self, username: str, password: str, database: str | None) -> bool:
        if self.roles.get(username) != password:
            return False
        return database is None or self.databases.get(database) == username
