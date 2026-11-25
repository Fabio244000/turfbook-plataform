# Texts of the db-provisioner: error messages (callers read them next to `errorType`)
# and log messages. None of them ever includes the password.

IDENTIFIER_RULE = '{key} must be a lowercase identifier ({pattern})'
PASSWORD_RULE = 'password must have at least 15 characters, letters and digits only'
UNKNOWN_ACTION = 'action must be "drop", or be left out to create'
DROP_DB_NAME_RULE = 'db_name must start with "{prefix}" to be dropped'
DROP_USERNAME_RULE = 'username must end with "{suffix}" to be dropped'

DATABASE_ALREADY_PROVISIONED = 'A database named "{db_name}" is already provisioned'
USER_ALREADY_EXISTS = 'A user named "{username}" already exists'
NOT_AUTHORIZED = (
    'Not authorized to drop the database "{db_name}" and the user "{username}": '
    'the user must own the database and its password must connect'
)

RESULT_LOG = 'Database %s, user %s: %s'
