import base64
import hashlib

from cryptography.fernet import Fernet

from app.config import settings

_key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest())
_fernet = Fernet(_key)


def encrypt(plaintext: str | None) -> str | None:
    if plaintext is None:
        return None
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str | None) -> str | None:
    if ciphertext is None:
        return None
    return _fernet.decrypt(ciphertext.encode()).decode()
