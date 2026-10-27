class FakeDatabaseAdmin:
    def __init__(
        self,
        databases: set[str] | None = None,
        roles: set[str] | None = None,
        create_database_error: Exception | None = None,
    ) -> None:
        self.databases = databases or set()
        self.roles: dict[str, str | None] = dict.fromkeys(roles or set())
        self.owners: dict[str, str] = {}
        self._create_database_error = create_database_error

    def database_exists(self, name: str) -> bool:
        return name in self.databases

    def role_exists(self, name: str) -> bool:
        return name in self.roles

    def create_role(self, name: str, password: str) -> None:
        self.roles[name] = password

    def drop_role(self, name: str) -> None:
        self.roles.pop(name, None)

    def create_database(self, name: str, owner: str) -> None:
        if self._create_database_error is not None:
            raise self._create_database_error
        self.databases.add(name)
        self.owners[name] = owner
