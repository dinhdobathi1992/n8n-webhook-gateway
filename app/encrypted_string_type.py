from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

from app.crypto import decrypt, encrypt


class EncryptedString(TypeDecorator):
    impl = String
    cache_ok = True

    def __init__(self, length: int = 2048, **kwargs):
        super().__init__(length=length, **kwargs)

    def process_bind_param(self, value, dialect):
        return encrypt(value)

    def process_result_value(self, value, dialect):
        return decrypt(value)
