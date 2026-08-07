"""Password hashing (bcrypt) and JWT issuing/verification (python-jose).

Pure functions, no DB access — kept separate from auth_service.py so they're
unit-testable without a database (Section 12, rule 3: test-first).
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()

TokenType = Literal["access", "refresh"]


class InvalidTokenError(Exception):
    """Raised for any expired/malformed/wrong-type JWT — callers turn this
    into a 401, never leak whether it was expiry vs. tampering vs. wrong type."""


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


def _create_token(user_id: uuid.UUID, token_type: TokenType, expires_delta: timedelta) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: uuid.UUID) -> str:
    return _create_token(user_id, "access", timedelta(minutes=settings.access_token_expire_minutes))


def create_refresh_token(user_id: uuid.UUID) -> str:
    return _create_token(user_id, "refresh", timedelta(days=settings.refresh_token_expire_days))


def decode_token(token: str, expected_type: TokenType) -> uuid.UUID:
    """Returns the user id encoded in the token, or raises InvalidTokenError.
    Rejects a refresh token presented as an access token and vice versa —
    the whole point of the `type` claim."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise InvalidTokenError("Token is invalid or expired.") from exc

    if payload.get("type") != expected_type:
        raise InvalidTokenError(f"Expected a {expected_type} token.")

    try:
        return uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise InvalidTokenError("Token subject is malformed.") from exc


def create_invite_token(org_id: uuid.UUID, email: str, role: str) -> str:
    """Section 7, Module 2: 'invite = a signed link in dev, not a real email.'
    A self-contained signed token stands in for a real invite-email system —
    no pending-invite table needed, the token itself carries everything
    `accept_invite` needs to verify and complete the membership."""
    now = datetime.now(UTC)
    claims = {
        "type": "invite",
        "org_id": str(org_id),
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + timedelta(days=7),
    }
    return jwt.encode(claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_invite_token(token: str) -> dict:
    """Returns {org_id, email, role} or raises InvalidTokenError."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise InvalidTokenError("Invite link is invalid or expired.") from exc

    if payload.get("type") != "invite":
        raise InvalidTokenError("Not an invite token.")

    try:
        return {
            "org_id": uuid.UUID(payload["org_id"]),
            "email": payload["email"],
            "role": payload["role"],
        }
    except (KeyError, ValueError) as exc:
        raise InvalidTokenError("Invite token is malformed.") from exc
