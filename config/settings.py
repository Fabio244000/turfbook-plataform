from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # The admin connection of the shared PostgreSQL instance (the RDS master user).
    master_db_host: str
    master_db_port: int = 5432
    master_db_user: str
    master_db_password: str
    master_db_name: str = 'postgres'
    master_db_connect_timeout: int = 10
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')


settings = Settings()
