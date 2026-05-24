"""
tokens.py — JWT and refresh token utilities for mcp-auth.

Access tokens:  JWT, 15-min TTL, signed with JWT_SECRET.
Refresh tokens: random UUID, hashed before DB storage, 30-day TTL.
Blacklist:      revoked access tokens stored in Redis until natural expiry.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import redis as redis_lib
from jose import JWTError, jwt

from src.config import settings


# ── Redis client for blacklist ────────────────────────────────────────────────

def _get_redis() -> redis_lib.Redis:
    return redis_lib.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
    )


# ── Access tokens ─────────────────────────────────────────────────────────────

def create_access_token(
    user_id: str,
    global_role: str,
    app_roles: list[dict],  # [{"app": "marketplace", "roles": ["seller"]}]
) -> str:
    """Create a signed JWT access token."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "global_role": global_role,
        "app_roles": app_roles,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any] | None:
    """
    Decode and validate a JWT access token.
    Returns the payload dict, or None if invalid/expired.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


def is_token_blacklisted(token: str) -> bool:
    """Check if an access token has been blacklisted (logged out)."""
    try:
        r = _get_redis()
        token_id = _token_id(token)
        return bool(r.exists(f"auth:blacklist:{token_id}"))
    except Exception:
        return False  # fail open — don't block requests if Redis is down


def blacklist_token(token: str) -> None:
    """
    Add an access token to the blacklist until it naturally expires.
    Called on logout.
    """
    payload = decode_access_token(token)
    if not payload:
        return
    try:
        r = _get_redis()
        exp = payload.get("exp", 0)
        now = datetime.now(timezone.utc).timestamp()
        ttl = max(1, int(exp - now))
        token_id = _token_id(token)
        r.setex(f"auth:blacklist:{token_id}", ttl, "1")
    except Exception:
        pass  # non-fatal — token will expire naturally


def _token_id(token: str) -> str:
    """Short hash of a token for use as a Redis key."""
    return hashlib.sha256(token.encode()).hexdigest()[:32]


# ── Refresh tokens ────────────────────────────────────────────────────────────

def generate_refresh_token() -> tuple[str, str]:
    """
    Generate a refresh token.
    Returns (raw_token, hashed_token).
    Store the hash in the DB. Send the raw token to the client.
    """
    raw = secrets.token_urlsafe(48)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


def hash_refresh_token(raw: str) -> str:
    """Hash a raw refresh token for DB lookup."""
    return hashlib.sha256(raw.encode()).hexdigest()
