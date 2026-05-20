from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    port: int = 3000
    database_url: str = "sqlite+aiosqlite:///./gateway.db"
    secret_key: str = "change-me"
    encryption_key: str | None = None
    legacy_encryption_keys: str = ""
    allow_weak_secrets: bool = False
    admin_username: str = "admin"
    admin_password: str = "admin"
    public_base_url: str = "http://localhost:3000"
    force_https_cookies: bool = True
    trusted_proxy_depth: int = 0
    allowed_origins: str = ""
    forward_timeout_seconds: int = 30
    forward_max_retries: int = 3
    forward_retry_base_seconds: int = 1
    webhook_rate_limit_per_min: int = 200
    webhook_max_body_bytes: int = 1_048_576
    allowed_internal_hosts: str = ""
    block_private_destination_ips: bool = True
    security_headers_enabled: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
