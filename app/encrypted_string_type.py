from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

from app.crypto import decrypt, encrypt


class EncryptedString(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return encrypt(value)

    def process_result_value(self, value, dialect):
        return decrypt(value)
