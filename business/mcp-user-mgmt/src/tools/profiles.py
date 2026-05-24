"""
profiles.py — User profile tools.

create_profile() — create extended profile for a user
get_profile()    — fetch full profile
update_profile() — update profile fields
"""

import uuid
from datetime import datetime, timezone
from typing import Any

import psycopg2

from src.db import dict_cursor, get_conn

ALLOWED_FIELDS = {"display_name", "bio", "avatar_url", "location", "website", "timezone"}


def run_create_profile(
    user_id: str,
    display_name: str | None = None,
    bio: str | None = None,
    avatar_url: str | None = None,
    location: str | None = None,
    website: str | None = None,
    timezone: str | None = None,
) -> dict[str, Any]:
    """
    Create an extended profile for a user.

    Called after register() to set up the user's public-facing identity.
    Avatar URL should be set after uploading via mcp-storage.

    Args:
        user_id:      UUID from mcp-auth users table.
        display_name: Public name shown in the app.
        bio:          Short bio or description.
        avatar_url:   URL of profile image (from mcp-storage).
        location:     City or country.
        website:      Personal or professional website.
        timezone:     IANA timezone (e.g. "Europe/Vienna").
    """
    now = datetime.now(timezone.utc)
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("SELECT id FROM users WHERE id = %s", [user_id])
                if not cur.fetchone():
                    return {"ok": False, "error": f"User '{user_id}' not found in users table."}

                cur.execute("SELECT id FROM user_profiles WHERE user_id = %s", [user_id])
                if cur.fetchone():
                    return {"ok": False, "error": f"Profile already exists for user '{user_id}'. Use update_profile."}

                profile_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO user_profiles
                        (id, user_id, display_name, bio, avatar_url, location, website, timezone, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [profile_id, user_id, display_name, bio, avatar_url,
                      location, website, timezone, now, now])

        return {
            "ok": True,
            "profile_id": profile_id,
            "user_id": user_id,
            "display_name": display_name,
        }
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_get_profile(user_id: str) -> dict[str, Any]:
    """
    Fetch the full profile for a user.

    Args:
        user_id: UUID of the user.
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    SELECT p.*, u.email, u.phone, u.username,
                           u.global_role, u.is_active, u.is_verified,
                           u.created_at AS account_created_at
                    FROM user_profiles p
                    JOIN users u ON u.id = p.user_id
                    WHERE p.user_id = %s
                """, [user_id])
                row = cur.fetchone()

        if not row:
            return {"ok": False, "error": f"No profile found for user '{user_id}'. Run create_profile first."}

        return {"ok": True, "profile": dict(row)}
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_update_profile(user_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    """
    Update profile fields.

    Allowed fields: display_name, bio, avatar_url, location, website, timezone.

    Args:
        user_id: UUID of the user.
        fields:  Dict of fields to update.
    """
    updates = {k: v for k, v in fields.items() if k in ALLOWED_FIELDS}
    if not updates:
        return {
            "ok": False,
            "error": f"No valid fields. Allowed: {', '.join(sorted(ALLOWED_FIELDS))}",
        }

    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                set_clause = ", ".join(f"{k} = %s" for k in updates)
                values = list(updates.values()) + [datetime.now(timezone.utc), user_id]
                cur.execute(
                    f"UPDATE user_profiles SET {set_clause}, updated_at = %s WHERE user_id = %s RETURNING id",
                    values,
                )
                if not cur.fetchone():
                    return {"ok": False, "error": f"No profile found for '{user_id}'. Run create_profile first."}

        return {"ok": True, "user_id": user_id, "updated_fields": list(updates.keys())}
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}
