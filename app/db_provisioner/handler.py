import logging

from psycopg import connect

from app.db_provisioner import messages
from app.db_provisioner.postgres_admin import (
    PostgresDatabaseAdmin,
    PostgresLoginChecker,
)
from app.db_provisioner.provisioner import execute, parse_request
from config.settings import settings

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: dict[str, object], context: object) -> dict[str, str]:
    """Invoked directly (aws lambda invoke). Never log the event: it holds the
    password. Errors are raised so Lambda reports them as FunctionError."""
    request = parse_request(event)
    logins = PostgresLoginChecker(
        host=settings.master_db_host,
        port=settings.master_db_port,
        connect_timeout=settings.master_db_connect_timeout,
        maintenance_db=settings.master_db_name,
    )
    with connect(
        host=settings.master_db_host,
        port=settings.master_db_port,
        user=settings.master_db_user,
        password=settings.master_db_password,
        dbname=settings.master_db_name,
        connect_timeout=settings.master_db_connect_timeout,
        autocommit=True,
    ) as connection:
        result = execute(request, PostgresDatabaseAdmin(connection), logins)
    logger.info(
        messages.RESULT_LOG, request.db_name, request.username, result['status']
    )
    return result
