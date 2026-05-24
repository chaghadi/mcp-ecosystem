"""
server.py — mcp-auth MCP server entry point.

Implemented tools:
  register, login, logout, refresh_access_token, verify_token
  create_app, create_role, assign_role, revoke_role,
  get_user_roles, list_app_roles
  get_user, update_user, deactivate_user, list_users
  run_migrations, health_check

Stubs (registered, not yet implemented):
  oauth_redirect, oauth_callback, send_verification, verify_code
"""

import subprocess
from typing import Any

from mcp.server.fastmcp import FastMCP

from src.config import settings
from src.db import get_conn
from src.tools import auth as _auth
from src.tools import roles as _roles
from src.tools import stubs as _stubs
from src.tools import users as _users

mcp = FastMCP(
    "mcp-auth",
    instructions=(
        "Auth MCP for mmiri28 solutions. "
        "Handles registration, login, JWT tokens, and app-scoped roles. "
        "Supports email, phone, and username auth. Google OAuth is a stub for future use."
    ),
)


# ── Health ────────────────────────────────────────────────────────────────────

@mcp.tool()
def health_check() -> dict:
    """Verify database and Redis connectivity for mcp-auth."""
    results = {}
    error = settings.validate()
    if error:
        return {"ok": False, "error": error}

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM users")
                results["users"] = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM apps")
                results["apps"] = cur.fetchone()[0]
        results["postgres"] = "connected"
    except Exception as exc:
        results["postgres"] = f"error: {exc}"

    try:
        import redis
        r = redis.from_url(settings.redis_url, socket_connect_timeout=3)
        r.ping()
        results["redis"] = "connected"
    except Exception as exc:
        results["redis"] = f"error: {exc}"

    ok = results.get("postgres") == "connected" and results.get("redis") == "connected"
    return {"ok": ok, "checks": results}


@mcp.tool()
def run_migrations() -> dict:
    """Run pending Alembic migrations for the auth schema."""
    error = settings.validate()
    if error:
        return {"ok": False, "error": error}
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        capture_output=True, text=True,
        cwd=str(settings.mcp_root),
    )
    if result.returncode != 0:
        return {"ok": False, "error": result.stderr or result.stdout}
    return {"ok": True, "output": result.stdout or "Migrations applied."}


# ── Authentication ────────────────────────────────────────────────────────────

@mcp.tool()
def register(
    identifier: str,
    password: str,
    auth_method: str = "email",
    app_slug: str | None = None,
    initial_role: str | None = None,
) -> dict:
    """
    Register a new user account.

    Args:
        identifier:   Email, phone number, or username.
        password:     Plain text password (min 8 chars).
        auth_method:  "email" | "phone" | "username"
        app_slug:     Optionally assign initial_role in this app on registration.
        initial_role: Role to assign (requires app_slug).
    """
    return _auth.run_register(
        identifier=identifier, password=password,
        auth_method=auth_method, app_slug=app_slug, initial_role=initial_role,
    )


@mcp.tool()
def login(
    identifier: str,
    password: str,
    auth_method: str = "email",
    app_slug: str | None = None,
) -> dict:
    """
    Authenticate a user. Returns access_token and refresh_token.

    Args:
        identifier:  Email, phone, or username.
        password:    Plain text password.
        auth_method: "email" | "phone" | "username"
        app_slug:    Include this app's roles in the token.
    """
    return _auth.run_login(
        identifier=identifier, password=password,
        auth_method=auth_method, app_slug=app_slug,
    )


@mcp.tool()
def logout(refresh_token: str, access_token: str | None = None) -> dict:
    """
    Revoke a refresh token and optionally blacklist the access token.

    Args:
        refresh_token: The refresh token to revoke.
        access_token:  Optionally blacklist this token immediately.
    """
    return _auth.run_logout(refresh_token=refresh_token, access_token=access_token)


@mcp.tool()
def refresh_access_token(refresh_token: str) -> dict:
    """
    Exchange a valid refresh token for a new access token.

    Args:
        refresh_token: The refresh token issued at login.
    """
    return _auth.run_refresh_access_token(refresh_token=refresh_token)


@mcp.tool()
def verify_token(access_token: str, app_slug: str | None = None) -> dict:
    """
    Validate an access token and return user identity and roles.

    Args:
        access_token: JWT to validate.
        app_slug:     Return roles specific to this app.
    """
    return _auth.run_verify_token(access_token=access_token, app_slug=app_slug)


# ── Role management ───────────────────────────────────────────────────────────

@mcp.tool()
def create_app(slug: str, name: str) -> dict:
    """
    Register an app in the ecosystem.

    Must be done before creating roles for it.

    Args:
        slug: URL-safe identifier (e.g. "marketplace").
        name: Human-readable name (e.g. "mmiri28 Marketplace").
    """
    return _roles.run_create_app(slug=slug, name=name)


@mcp.tool()
def create_role(app_slug: str, role_name: str, description: str = "") -> dict:
    """
    Define a role for an app.

    Args:
        app_slug:    The app this role belongs to.
        role_name:   Role identifier (e.g. "seller", "buyer").
        description: Optional description.
    """
    return _roles.run_create_role(
        app_slug=app_slug, role_name=role_name, description=description
    )


@mcp.tool()
def assign_role(
    user_id: str,
    app_slug: str,
    role_name: str,
    assigned_by_user_id: str | None = None,
) -> dict:
    """
    Assign a role to a user in an app.

    Args:
        user_id:             The user.
        app_slug:            The app context.
        role_name:           The role to assign.
        assigned_by_user_id: Who is making the assignment.
    """
    return _roles.run_assign_role(
        user_id=user_id, app_slug=app_slug,
        role_name=role_name, assigned_by_user_id=assigned_by_user_id,
    )


@mcp.tool()
def revoke_role(user_id: str, app_slug: str, role_name: str) -> dict:
    """
    Remove a role from a user in an app.

    Args:
        user_id:   The user.
        app_slug:  The app context.
        role_name: The role to remove.
    """
    return _roles.run_revoke_role(
        user_id=user_id, app_slug=app_slug, role_name=role_name
    )


@mcp.tool()
def get_user_roles(user_id: str, app_slug: str | None = None) -> dict:
    """
    Get all roles for a user, optionally filtered to one app.

    Args:
        user_id:  The user.
        app_slug: Filter to a specific app (optional).
    """
    return _roles.run_get_user_roles(user_id=user_id, app_slug=app_slug)


@mcp.tool()
def list_app_roles(app_slug: str) -> dict:
    """
    List all defined roles for an app.

    Args:
        app_slug: The app to list roles for.
    """
    return _roles.run_list_app_roles(app_slug=app_slug)


# ── User management ───────────────────────────────────────────────────────────

@mcp.tool()
def get_user(identifier: str) -> dict:
    """
    Look up a user by UUID, email, phone, or username.

    Args:
        identifier: UUID, email, phone number, or username.
    """
    return _users.run_get_user(identifier=identifier)


@mcp.tool()
def update_user(user_id: str, fields: dict[str, Any]) -> dict:
    """
    Update user fields. Allowed: email, phone, username, is_verified.

    Args:
        user_id: UUID of the user.
        fields:  Dict of fields to update.
    """
    return _users.run_update_user(user_id=user_id, fields=fields)


@mcp.tool()
def deactivate_user(user_id: str) -> dict:
    """
    Deactivate a user account (soft delete). Revokes all refresh tokens.

    Args:
        user_id: UUID of the user to deactivate.
    """
    return _users.run_deactivate_user(user_id=user_id)


@mcp.tool()
def list_users(
    app_slug: str | None = None,
    role_name: str | None = None,
    page: int = 1,
    limit: int = 50,
) -> dict:
    """
    List users with optional filtering by app and role.

    Args:
        app_slug:  Filter to users in this app.
        role_name: Filter to users with this role.
        page:      Page number. Default: 1.
        limit:     Results per page. Default: 50. Max: 200.
    """
    return _users.run_list_users(
        app_slug=app_slug, role_name=role_name, page=page, limit=limit
    )


# ── OAuth stubs ───────────────────────────────────────────────────────────────

@mcp.tool()
def oauth_redirect(provider: str, app_slug: str) -> dict:
    """
    [STUB] Get the OAuth redirect URL for a provider.
    provider: "google" | "github"
    """
    return _stubs.run_oauth_redirect(provider=provider, app_slug=app_slug)


@mcp.tool()
def oauth_callback(provider: str, code: str, state: str) -> dict:
    """[STUB] Handle OAuth provider callback. Returns JWT tokens on success."""
    return _stubs.run_oauth_callback(provider=provider, code=code, state=state)


@mcp.tool()
def send_verification(user_id: str, method: str = "email") -> dict:
    """[STUB] Send verification code. Requires mcp-notifications."""
    return _stubs.run_send_verification(user_id=user_id, method=method)


@mcp.tool()
def verify_code(user_id: str, code: str) -> dict:
    """[STUB] Verify email/phone code. Sets is_verified=true on success."""
    return _stubs.run_verify_code(user_id=user_id, code=code)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
