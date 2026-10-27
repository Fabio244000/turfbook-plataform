import logging

from psycopg import connect

from app.db_provisioner.postgres_admin import PostgresDatabaseAdmin
from app.db_provisioner.provisioner import ProvisionRequest, provision
from config.settings import settings

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: dict[str, object], context: object) -> dict[str, str]:
    """Invoked directly (aws lambda invoke). Never log the event: it holds the
    password. Errors are raised so Lambda reports them as FunctionError."""
    request = ProvisionRequest.from_event(event)
    with connect(
        host=settings.master_db_host,
        port=settings.master_db_port,
        user=settings.master_db_user,
        password=settings.master_db_password,
        dbname=settings.master_db_name,
        connect_timeout=settings.master_db_connect_timeout,
        autocommit=True,
    ) as connection:
        result = provision(request, PostgresDatabaseAdmin(connection))
    logger.info('Provisioned database %s for %s', request.db_name, request.username)
    return result
