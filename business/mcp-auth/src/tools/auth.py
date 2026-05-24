"""
auth.py — Core authentication tools.

register()             — create a new user account
login()                — authenticate and return JWT tokens
logout()               — revoke refresh token + blacklist access token
refresh_access_token() — get a new access token from a valid refresh token
verify_token()         — validate an access token, return user + roles
"""

import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt as _bcrypt
import psycopg2

from src.config import settings
from src.db import dict_cursor, get_conn
from src.tools.tokens import (
    blacklist_token,
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_refresh_token,
    is_token_blacklisted,
)

VALID_AUTH_METHODS = {"email", "phone", "username"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode(), hashed.encode())


def _validate_password_strength(password: str) -> str | None:
    if len(password) < 8:
        return "Password must be at least 8 characters."
    return None


def _get_user_app_roles(conn, user_id: str) -> list[dict]:
    """Return app roles for a user grouped by app slug."""
    with dict_cursor(conn) as cur:
        cur.execute("""
            SELECT a.slug AS app, ar.name AS role
            FROM user_app_roles uar
            JOIN apps a ON a.id = uar.app_id
            JOIN app_roles ar ON ar.id = uar.role_id
            WHERE uar.user_id = %s
            ORDER BY a.slug, ar.name
        """, [user_id])
        rows = cur.fetchall()

    grouped: dict[str, list[str]] = {}
    for row in rows:
        grouped.setdefault(row["app"], []).append(row["role"])
    return [{"app": app, "roles": roles} for app, roles in grouped.items()]


# ── Register ──────────────────────────────────────────────────────────────────

def run_register(
    identifier: str,
    password: str,
    auth_method: str = "email",
    app_slug: str | None = None,
    initial_role: str | None = None,
) -> dict[str, Any]:
    """
    Register a new user account.

    Args:
        identifier:   Email, phone number, or username depending on auth_method.
        password:     Plain text password (will be hashed).
        auth_method:  "email" | "phone" | "username"
        app_slug:     If provided, assign initial_role in this app after registration.
        initial_role: Role to assign in app_slug (requires app_slug).

    Returns:
        ok, user_id, global_role, access_token, refresh_token.
    """
    if auth_method not in VALID_AUTH_METHODS:
        return {"ok": False, "error": f"auth_method must be one of: {', '.join(VALID_AUTH_METHODS)}"}

    identifier = identifier.strip()
    if not identifier:
        return {"ok": False, "error": "identifier cannot be empty."}

    pwd_error = _validate_password_strength(password)
    if pwd_error:
        return {"ok": False, "error": pwd_error}

    # Determine global role
    global_role = "superadmin" if (
        auth_method == "email" and
        settings.superadmin_email and
        identifier.lower() == settings.superadmin_email
    ) else "user"

    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                # Check for duplicate
                col = auth_method  # email | phone | username
                cur.execute(f"SELECT id FROM users WHERE {col} = %s", [identifier])
                if cur.fetchone():
                    return {"ok": False, "error": f"{auth_method.capitalize()} already registered."}

                user_id = str(uuid.uuid4())
                password_hash = _hash_password(password)
                now = datetime.now(timezone.utc)

                cur.execute("""
                    INSERT INTO users (id, email, phone, username, password_hash,
                                       global_role, is_active, is_verified, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, true, false, %s, %s)
                """, [
                    user_id,
                    identifier if auth_method == "email" else None,
                    identifier if auth_method == "phone" else None,
                    identifier if auth_method == "username" else None,
                    password_hash,
                    global_role,
                    now, now,
                ])

                # Assign initial app role if provided
                if app_slug and initial_role:
                    cur.execute("SELECT id FROM apps WHERE slug = %s", [app_slug])
                    app_row = cur.fetchone()
                    if app_row:
                        cur.execute(
                            "SELECT id FROM app_roles WHERE app_id = %s AND name = %s",
                            [app_row["id"], initial_role]
                        )
                        role_row = cur.fetchone()
                        if role_row:
                            cur.execute("""
                                INSERT INTO user_app_roles (id, user_id, app_id, role_id, assigned_at)
                                VALUES (%s, %s, %s, %s, %s)
                                ON CONFLICT DO NOTHING
                            """, [str(uuid.uuid4()), user_id, app_row["id"], role_row["id"], now])

                # Create refresh token
                raw_refresh, hashed_refresh = generate_refresh_token()
                expires_at = now + timedelta(days=settings.refresh_token_expire_days)
                cur.execute("""
                    INSERT INTO refresh_tokens (id, user_id, token_hash, app_slug, expires_at, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, [str(uuid.uuid4()), user_id, hashed_refresh, app_slug, expires_at, now])

            app_roles = _get_user_app_roles(conn, user_id)
            access_token = create_access_token(user_id, global_role, app_roles)

        return {
            "ok": True,
            "user_id": user_id,
            "global_role": global_role,
            "auth_method": auth_method,
            "access_token": access_token,
            "refresh_token": raw_refresh,
            "expires_in": settings.access_token_expire_minutes * 60,
        }

    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


# ── Login ─────────────────────────────────────────────────────────────────────

def run_login(
    identifier: str,
    password: str,
    auth_method: str = "email",
    app_slug: str | None = None,
) -> dict[str, Any]:
    """
    Authenticate a user and return JWT tokens.

    Args:
        identifier:  Email, phone, or username.
        password:    Plain text password.
        auth_method: "email" | "phone" | "username"
        app_slug:    Optional — used to include app-specific roles in the token.

    Returns:
        ok, user_id, global_role, access_token, refresh_token.
    """
    if auth_method not in VALID_AUTH_METHODS:
        return {"ok": False, "error": f"auth_method must be one of: {', '.join(VALID_AUTH_METHODS)}"}

    identifier = identifier.strip()

    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                col = auth_method
                cur.execute(
                    f"SELECT id, password_hash, global_role, is_active FROM users WHERE {col} = %s",
                    [identifier]
                )
                user = cur.fetchone()

            if not user:
                return {"ok": False, "error": "Invalid credentials."}

            if not user["is_active"]:
                return {"ok": False, "error": "Account is deactivated."}

            if not _verify_password(password, user["password_hash"]):
                return {"ok": False, "error": "Invalid credentials."}

            user_id = user["id"]
            global_role = user["global_role"]

            # Revoke old refresh tokens for this user+app
            with dict_cursor(conn) as cur:
                cur.execute("""
                    UPDATE refresh_tokens
                    SET revoked_at = NOW()
                    WHERE user_id = %s
                      AND app_slug IS NOT DISTINCT FROM %s
                      AND revoked_at IS NULL
                      AND expires_at > NOW()
                """, [user_id, app_slug])

            # Create new refresh token
            raw_refresh, hashed_refresh = generate_refresh_token()
            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(days=settings.refresh_token_expire_days)

            with dict_cursor(conn) as cur:
                cur.execute("""
                    INSERT INTO refresh_tokens (id, user_id, token_hash, app_slug, expires_at, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, [str(uuid.uuid4()), user_id, hashed_refresh, app_slug, expires_at, now])

            app_roles = _get_user_app_roles(conn, user_id)
            access_token = create_access_token(user_id, global_role, app_roles)

        return {
            "ok": True,
            "user_id": user_id,
            "global_role": global_role,
            "access_token": access_token,
            "refresh_token": raw_refresh,
            "expires_in": settings.access_token_expire_minutes * 60,
        }

    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


# ── Logout ────────────────────────────────────────────────────────────────────

def run_logout(refresh_token: str, access_token: str | None = None) -> dict[str, Any]:
    """
    Revoke a refresh token and optionally blacklist the current access token.

    Args:
        refresh_token: The refresh token to revoke.
        access_token:  Optional — blacklist this access token immediately.
    """
    token_hash = hash_refresh_token(refresh_token)
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    UPDATE refresh_tokens
                    SET revoked_at = NOW()
                    WHERE token_hash = %s AND revoked_at IS NULL
                    RETURNING id
                """, [token_hash])
                revoked = cur.fetchone()

        if access_token:
            blacklist_token(access_token)

        return {
            "ok": True,
            "revoked": revoked is not None,
            "message": "Logged out successfully.",
        }
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


# ── Refresh ───────────────────────────────────────────────────────────────────

def run_refresh_access_token(refresh_token: str) -> dict[str, Any]:
    """
    Exchange a valid refresh token for a new access token.

    Args:
        refresh_token: The refresh token issued at login.
    """
    token_hash = hash_refresh_token(refresh_token)
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    SELECT rt.user_id, u.global_role, u.is_active
                    FROM refresh_tokens rt
                    JOIN users u ON u.id = rt.user_id
                    WHERE rt.token_hash = %s
                      AND rt.revoked_at IS NULL
                      AND rt.expires_at > NOW()
                """, [token_hash])
                row = cur.fetchone()

            if not row:
                return {"ok": False, "error": "Refresh token is invalid or expired."}

            if not row["is_active"]:
                return {"ok": False, "error": "Account is deactivated."}

            app_roles = _get_user_app_roles(conn, row["user_id"])
            access_token = create_access_token(row["user_id"], row["global_role"], app_roles)

        return {
            "ok": True,
            "access_token": access_token,
            "expires_in": settings.access_token_expire_minutes * 60,
        }
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


# ── Verify token ──────────────────────────────────────────────────────────────

def run_verify_token(access_token: str, app_slug: str | None = None) -> dict[str, Any]:
    """
    Validate an access token and return the user's identity and roles.

    Args:
        access_token: The JWT access token to verify.
        app_slug:     Optional — if provided, also return roles in this specific app.

    Returns:
        ok, user_id, global_role, app_roles, roles_in_app (if app_slug given).
    """
    if is_token_blacklisted(access_token):
        return {"ok": False, "error": "Token has been revoked."}

    payload = decode_access_token(access_token)
    if not payload:
        return {"ok": False, "error": "Token is invalid or expired."}

    all_app_roles: list[dict] = payload.get("app_roles", [])

    roles_in_app: list[str] = []
    if app_slug:
        for entry in all_app_roles:
            if entry.get("app") == app_slug:
                roles_in_app = entry.get("roles", [])
                break

    return {
        "ok": True,
        "user_id": payload["sub"],
        "global_role": payload.get("global_role", "user"),
        "app_roles": all_app_roles,
        "roles_in_app": roles_in_app,
        "app_slug": app_slug,
        "is_superadmin": payload.get("global_role") == "superadmin",
    }
