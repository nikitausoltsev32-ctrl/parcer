from cryptography.fernet import Fernet

from app.core.config import settings


def _fernet() -> Fernet:
    key = settings.fernet_key
    if not key:
        raise RuntimeError("FERNET_KEY is not set")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_password(password: str) -> bytes:
    return _fernet().encrypt(password.encode())


def decrypt_password(encrypted: bytes) -> str:
    return _fernet().decrypt(encrypted).decode()
