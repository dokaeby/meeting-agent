import base64
import hashlib
import json
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from cryptography.fernet import Fernet, InvalidToken

hasher = PasswordHasher()


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def token() -> str:
    return secrets.token_urlsafe(32)


def password_hash(value: str) -> str:
    return hasher.hash(value)


def verify_password(value: str, encoded: str) -> bool:
    try:
        return hasher.verify(encoded, value)
    except (VerificationError, InvalidHashError):
        return False


def cipher(secret: str) -> Fernet:
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest()))


def encrypt(value: dict, secret: str) -> str:
    return cipher(secret).encrypt(json.dumps(value).encode()).decode()


def decrypt(value: str, secret: str) -> dict:
    try:
        return json.loads(cipher(secret).decrypt(value.encode()))
    except InvalidToken as exc:
        raise ValueError("invalid encrypted credential") from exc


def snapshot(value) -> str:
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
