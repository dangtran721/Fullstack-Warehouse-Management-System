import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import get_settings


password_hasher = PasswordHasher()


class TokenValidationError(Exception):
    """Raised when a JWT is malformed, expired, or used for the wrong purpose."""


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def hash_refresh_token(token: str) -> str:
    """Return a non-reversible identifier for server-side refresh token storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_token(
    *,
    subject: uuid.UUID,
    token_type: str,
    expires_delta: timedelta,
    additional_claims: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    settings = get_settings()
    issued_at = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": issued_at,
        "exp": issued_at + expires_delta,
        "type": token_type,
        "jti": str(uuid.uuid4()),
    }
    if additional_claims:
        payload.update(additional_claims)

    return (
        jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm),
        payload,
    )


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "iat", "exp", "type", "jti"]},
        )
    except jwt.PyJWTError as error:
        raise TokenValidationError from error

    if payload.get("type") != expected_type:
        raise TokenValidationError
    return payload
