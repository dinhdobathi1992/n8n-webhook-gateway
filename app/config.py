from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    port: int = 3000
    database_url: str = "sqlite+aiosqlite:///./gateway.db"
    secret_key: str = "change-me"
    admin_username: str = "admin"
    admin_password: str = "admin"
    public_base_url: str = "http://localhost:3000"
    forward_timeout_seconds: int = 30
    forward_max_retries: int = 3
    forward_retry_base_seconds: int = 1

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
