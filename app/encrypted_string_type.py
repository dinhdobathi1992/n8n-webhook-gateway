from sqlalchemy import String
from sqlalchemy.types import TypeDecorator
from cryptography.fernet import InvalidToken

from app.crypto import decrypt, encrypt


class EncryptedString(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return encrypt(value)

    def process_result_value(self, value, dialect):
        try:
            return decrypt(value)
        except InvalidToken:
            return value
