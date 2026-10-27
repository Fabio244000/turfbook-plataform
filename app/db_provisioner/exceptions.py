class ProvisioningError(Exception):
    """Base of every expected provisioner failure. Lambda reports the concrete class
    name as `errorType`, so callers can tell the cases apart."""


class InvalidPayloadError(ProvisioningError):
    pass


class DatabaseAlreadyProvisionedError(ProvisioningError):
    def __init__(self, db_name: str) -> None:
        super().__init__(f'A database named "{db_name}" is already provisioned')


class UserAlreadyExistsError(ProvisioningError):
    def __init__(self, username: str) -> None:
        super().__init__(f'A user named "{username}" already exists')
