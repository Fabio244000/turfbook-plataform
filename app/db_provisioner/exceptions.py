from app.db_provisioner import messages


class ProvisioningError(Exception):
    """Base of every expected provisioner failure. Lambda reports the concrete class
    name as `errorType`, so callers can tell the cases apart."""


class InvalidPayloadError(ProvisioningError):
    pass


class DatabaseAlreadyProvisionedError(ProvisioningError):
    def __init__(self, db_name: str) -> None:
        super().__init__(messages.DATABASE_ALREADY_PROVISIONED.format(db_name=db_name))


class UserAlreadyExistsError(ProvisioningError):
    def __init__(self, username: str) -> None:
        super().__init__(messages.USER_ALREADY_EXISTS.format(username=username))


class NotAuthorizedError(ProvisioningError):
    def __init__(self, db_name: str, username: str) -> None:
        super().__init__(
            messages.NOT_AUTHORIZED.format(db_name=db_name, username=username)
        )
