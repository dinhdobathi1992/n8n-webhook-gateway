from app.config import settings
from app.security import startup_security_errors


def test_startup_security_rejects_weak_defaults():
    old_values = (
        settings.allow_weak_secrets,
        settings.secret_key,
        settings.encryption_key,
        settings.admin_password,
    )
    try:
        settings.allow_weak_secrets = False
        settings.secret_key = "change-me"
        settings.encryption_key = None
        settings.admin_password = "admin"
        errors = startup_security_errors()
        assert any("SECRET_KEY" in err for err in errors)
        assert any("ENCRYPTION_KEY" in err for err in errors)
        assert any("ADMIN_PASSWORD" in err for err in errors)
    finally:
        (
            settings.allow_weak_secrets,
            settings.secret_key,
            settings.encryption_key,
            settings.admin_password,
        ) = old_values


def test_startup_security_allows_local_override():
    old_allow = settings.allow_weak_secrets
    try:
        settings.allow_weak_secrets = True
        assert startup_security_errors() == []
    finally:
        settings.allow_weak_secrets = old_allow
