"""
server.py — mcp-user-mgmt MCP server entry point.

Tools:
  Profiles:    create_profile, get_profile, update_profile
  Preferences: get_preferences, set_preference, set_preferences, delete_preference
  Lifecycle:   delete_user, export_user_data
  Search:      search_users
  Admin:       health_check, run_migrations
"""

import subprocess
from typing import Any

from mcp.server.fastmcp import FastMCP

from src.config import settings
from src.db import get_conn
from src.tools import lifecycle as _lifecycle
from src.tools import preferences as _prefs
from src.tools import profiles as _profiles
from src.tools import search as _search

mcp = FastMCP(
    "mcp-user-mgmt",
    instructions=(
        "User management MCP for mmiri28 solutions. "
        "Handles profiles, flexible app-namespaced preferences, "
        "GDPR deletion, data export, and user search. "
        "Depends on mcp-auth for the users table."
    ),
)


# ── Admin ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def health_check() -> dict:
    """Verify database connectivity and check table existence."""
    error = settings.validate()
    if error:
        return {"ok": False, "error": error}
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM user_profiles")
                profiles = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM user_preferences")
                preferences = cur.fetchone()[0]
        return {
            "ok": True,
            "status": "connected",
            "user_profiles": profiles,
            "user_preferences": preferences,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def run_migrations() -> dict:
    """Run pending Alembic migrations for the user-mgmt schema."""
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


# ── Profiles ──────────────────────────────────────────────────────────────────

@mcp.tool()
def create_profile(
    user_id: str,
    display_name: str | None = None,
    bio: str | None = None,
    avatar_url: str | None = None,
    location: str | None = None,
    website: str | None = None,
    timezone: str | None = None,
) -> dict:
    """
    Create an extended profile for a user.

    Call after register() to set up public-facing identity.
    Avatar URL comes from mcp-storage after uploading the image there.

    Args:
        user_id:      UUID from mcp-auth.
        display_name: Public name shown in the app.
        bio:          Short description.
        avatar_url:   Profile image URL (from mcp-storage).
        location:     City or country.
        website:      Personal website.
        timezone:     IANA timezone (e.g. "Europe/Vienna").
    """
    return _profiles.run_create_profile(
        user_id=user_id, display_name=display_name, bio=bio,
        avatar_url=avatar_url, location=location,
        website=website, timezone=timezone,
    )


@mcp.tool()
def get_profile(user_id: str) -> dict:
    """
    Fetch the full profile for a user, including auth fields.

    Args:
        user_id: UUID of the user.
    """
    return _profiles.run_get_profile(user_id=user_id)


@mcp.tool()
def update_profile(user_id: str, fields: dict[str, Any]) -> dict:
    """
    Update profile fields.

    Allowed: display_name, bio, avatar_url, location, website, timezone.

    Args:
        user_id: UUID of the user.
        fields:  Dict of fields to update.
    """
    return _profiles.run_update_profile(user_id=user_id, fields=fields)


# ── Preferences ───────────────────────────────────────────────────────────────

@mcp.tool()
def get_preferences(user_id: str, app_slug: str | None = None) -> dict:
    """
    Get preferences for a user.

    Preferences are namespaced by app. If app_slug is given, returns
    only that app's preferences. Otherwise returns all namespaces.

    Args:
        user_id:  UUID of the user.
        app_slug: Return only this app's preferences (optional).
    """
    return _prefs.run_get_preferences(user_id=user_id, app_slug=app_slug)


@mcp.tool()
def set_preference(
    user_id: str,
    key: str,
    value: Any,
    app_slug: str | None = None,
) -> dict:
    """
    Set a single preference key for a user.

    Args:
        user_id:  UUID of the user.
        key:      Preference key (e.g. "theme", "notifications").
        value:    Any JSON-serializable value.
        app_slug: Namespace. None = stored under "global".
    """
    return _prefs.run_set_preference(
        user_id=user_id, key=key, value=value, app_slug=app_slug
    )


@mcp.tool()
def set_preferences(
    user_id: str,
    preferences: dict[str, Any],
    app_slug: str | None = None,
) -> dict:
    """
    Set multiple preference keys at once (merges with existing).

    Args:
        user_id:     UUID of the user.
        preferences: Dict of key → value pairs.
        app_slug:    Namespace. None = stored under "global".
    """
    return _prefs.run_set_preferences(
        user_id=user_id, preferences=preferences, app_slug=app_slug
    )


@mcp.tool()
def delete_preference(
    user_id: str,
    key: str,
    app_slug: str | None = None,
) -> dict:
    """
    Delete a single preference key.

    Args:
        user_id:  UUID of the user.
        key:      Preference key to delete.
        app_slug: Namespace. None = "global".
    """
    return _prefs.run_delete_preference(
        user_id=user_id, key=key, app_slug=app_slug
    )


# ── Lifecycle ─────────────────────────────────────────────────────────────────

@mcp.tool()
def delete_user(user_id: str, reason: str = "") -> dict:
    """
    Permanently delete a user and all their data (GDPR right to erasure).

    This is irreversible. Cascades to all auth, profile, and preferences data.
    For temporary deactivation, use mcp-auth deactivate_user instead.

    Args:
        user_id: UUID of the user to delete.
        reason:  Optional reason for audit purposes.
    """
    return _lifecycle.run_delete_user(user_id=user_id, reason=reason)


@mcp.tool()
def export_user_data(user_id: str) -> dict:
    """
    Export all data held for a user (GDPR Article 20 — right to data portability).

    Returns structured dict of account, profile, preferences, and roles.
    Format as a downloadable JSON file for the user.

    Args:
        user_id: UUID of the user.
    """
    return _lifecycle.run_export_user_data(user_id=user_id)


# ── Search ────────────────────────────────────────────────────────────────────

@mcp.tool()
def search_users(
    query: str,
    app_slug: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict:
    """
    Search users by display name, email, username, or phone.

    Args:
        query:    Search term (min 2 characters).
        app_slug: Restrict to users with a role in this app.
        page:     Page number. Default: 1.
        limit:    Results per page. Default: 20. Max: 100.
    """
    return _search.run_search_users(
        query=query, app_slug=app_slug, page=page, limit=limit
    )


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
