import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import get_settings

TokenType = Literal["access", "challenge"]

_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=64 * 1024,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)

# Verified against when the email is unknown, so a miss costs the same argon2
# work as a hit. Without it, response timing separates "no such user" from
# "wrong password". (SECURITY.md 5.6)
_ABSENT_USER_HASH = _hasher.hash(secrets.token_urlsafe(32))


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _ABSENT_USER_HASH, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def create_token(
    *, user_id: int, role: str, typ: TokenType, minutes: int,
    extra: dict[str, Any] | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "role": role,
        "typ": typ,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
        "jti": secrets.token_urlsafe(8),
    }
    if extra:
        claims.update(extra)
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, *, expected_typ: TokenType) -> dict[str, Any] | None:
    settings = get_settings()
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            # A list of exactly one algorithm. "alg": "none" and HS/RS confusion
            # are both rejected here, not by our code. (SECURITY.md 5.10)
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "iat", "sub", "typ"]},
        )
    except jwt.PyJWTError:
        return None
    if claims.get("typ") != expected_typ:
        return None
    return claims


def new_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


# Plain sha256, not argon2, and deliberately so: the OTP is 6 digits with a
# 10-minute life and 5 attempts, and the reset token is 256 bits of CSPRNG.
# Neither is brute-forceable from the hash. Salting the OTP with user_id stops
# one rainbow table covering every user's million codes.
def hash_otp(user_id: int, code: str) -> str:
    return hashlib.sha256(f"{user_id}:{code}".encode()).hexdigest()


def new_reset_token() -> str:
    return secrets.token_urlsafe(32)


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def constant_time_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())
