from fastapi import Request

from app.config import settings

WEAK_SECRET_KEYS = {"", "change-me", "change-me-to-random-secret", "secret"}
WEAK_ADMIN_PASSWORDS = {"", "admin", "password", "changeme", "change-me", "CHANGE-ME"}


def csv_values(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def get_client_ip(request: Request) -> str:
    if settings.trusted_proxy_depth > 0:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            parts = [part.strip() for part in forwarded_for.split(",") if part.strip()]
            if parts:
                index = max(0, len(parts) - settings.trusted_proxy_depth - 1)
                return parts[index]
    return request.client.host if request.client else "unknown"


def startup_security_errors() -> list[str]:
    if settings.allow_weak_secrets:
        return []

    errors: list[str] = []
    if settings.secret_key in WEAK_SECRET_KEYS or len(settings.secret_key) < 32:
        errors.append("SECRET_KEY must be a random value with at least 32 characters")

    if settings.admin_password in WEAK_ADMIN_PASSWORDS or len(settings.admin_password) < 12:
        errors.append("ADMIN_PASSWORD must be changed from the default and be at least 12 characters")

    if not settings.encryption_key:
        errors.append("ENCRYPTION_KEY must be set separately from SECRET_KEY")
    elif settings.encryption_key == settings.secret_key:
        errors.append("ENCRYPTION_KEY must not equal SECRET_KEY")
    elif settings.encryption_key in WEAK_SECRET_KEYS or len(settings.encryption_key) < 32:
        errors.append("ENCRYPTION_KEY must be a random value with at least 32 characters")

    return errors
