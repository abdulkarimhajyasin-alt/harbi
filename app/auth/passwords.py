from passlib.context import CryptContext
from passlib.exc import MissingBackendError, PasswordValueError, UnknownHashError


MAX_PASSWORD_BYTES = 4096
PASSWORD_TOO_LONG_MESSAGE = "كلمة المرور طويلة جدا"

password_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto",
)


class PasswordValidationError(ValueError):
    pass


def password_byte_length(password: str) -> int:
    return len(password.encode("utf-8"))


def validate_password_length(password: str) -> None:
    if password_byte_length(password) > MAX_PASSWORD_BYTES:
        raise PasswordValidationError(PASSWORD_TOO_LONG_MESSAGE)


def hash_password(password: str) -> str:
    validate_password_length(password)
    return password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    validate_password_length(password)
    if not password_hash.startswith("$pbkdf2-sha256$"):
        return False
    try:
        return password_context.verify(password, password_hash)
    except (MissingBackendError, PasswordValueError, UnknownHashError, ValueError):
        return False
