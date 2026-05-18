import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings
from app.security import csv_values


def _fernet_for(secret: str) -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


def _primary_secret() -> str:
    return settings.encryption_key or settings.secret_key


def _decrypt_secrets() -> list[str]:
    secrets = [_primary_secret(), *csv_values(settings.legacy_encryption_keys)]
    if settings.secret_key not in secrets:
        secrets.append(settings.secret_key)
    return secrets


def encrypt(plaintext: str | None) -> str | None:
    if plaintext is None:
        return None
    return _fernet_for(_primary_secret()).encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str | None) -> str | None:
    if ciphertext is None:
        return None
    for secret in _decrypt_secrets():
        try:
            return _fernet_for(secret).decrypt(ciphertext.encode()).decode()
        except InvalidToken:
            continue
    raise InvalidToken
