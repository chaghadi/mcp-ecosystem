"""
preferences.py — User preferences tools.

Preferences are stored in a single JSONB column namespaced by app slug:
{
  "global":      { "timezone": "Europe/Vienna", "language": "en" },
  "marketplace": { "theme": "dark", "notifications": true },
  "saas-tool":   { "sidebar_collapsed": false }
}

When app_slug is None, preferences go under "global".
No schema migration needed to add new preference keys.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import psycopg2

from src.db import dict_cursor, get_conn


def _ns(app_slug: str | None) -> str:
    """Return the namespace key for a given app slug."""
    return app_slug or "global"


def _ensure_preferences_row(conn, user_id: str) -> None:
    """Create a preferences row for the user if one doesn't exist."""
    with dict_cursor(conn) as cur:
        cur.execute("""
            INSERT INTO user_preferences (id, user_id, preferences, updated_at)
            VALUES (%s, %s, '{}', NOW())
            ON CONFLICT (user_id) DO NOTHING
        """, [str(uuid.uuid4()), user_id])


def run_get_preferences(
    user_id: str,
    app_slug: str | None = None,
) -> dict[str, Any]:
    """
    Get preferences for a user.

    Args:
        user_id:  UUID of the user.
        app_slug: Return only this app's preferences. None = return all.

    Returns:
        preferences dict. If app_slug given, returns only that namespace.
    """
    try:
        with get_conn() as conn:
            _ensure_preferences_row(conn, user_id)
            with dict_cursor(conn) as cur:
                if app_slug:
                    cur.execute("""
                        SELECT preferences -> %s AS prefs
                        FROM user_preferences WHERE user_id = %s
                    """, [_ns(app_slug), user_id])
                    row = cur.fetchone()
                    prefs = row["prefs"] if row and row["prefs"] else {}
                else:
                    cur.execute(
                        "SELECT preferences FROM user_preferences WHERE user_id = %s",
                        [user_id]
                    )
                    row = cur.fetchone()
                    prefs = row["preferences"] if row else {}

        return {
            "ok": True,
            "user_id": user_id,
            "app_slug": app_slug or "all",
            "preferences": prefs,
        }
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_set_preference(
    user_id: str,
    key: str,
    value: Any,
    app_slug: str | None = None,
) -> dict[str, Any]:
    """
    Set a single preference key for a user.

    Args:
        user_id:  UUID of the user.
        key:      Preference key (e.g. "theme", "notifications").
        value:    Any JSON-serializable value.
        app_slug: Namespace. None = "global".
    """
    if not key or not key.strip():
        return {"ok": False, "error": "key cannot be empty."}

    ns = _ns(app_slug)
    try:
        with get_conn() as conn:
            _ensure_preferences_row(conn, user_id)
            with dict_cursor(conn) as cur:
                cur.execute("""
                    UPDATE user_preferences
                    SET preferences = jsonb_set(
                        preferences,
                        ARRAY[%s, %s],
                        %s::jsonb,
                        true
                    ),
                    updated_at = NOW()
                    WHERE user_id = %s
                """, [ns, key.strip(), json.dumps(value), user_id])

        return {
            "ok": True,
            "user_id": user_id,
            "namespace": ns,
            "key": key.strip(),
            "value": value,
        }
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_set_preferences(
    user_id: str,
    preferences: dict[str, Any],
    app_slug: str | None = None,
) -> dict[str, Any]:
    """
    Set multiple preference keys at once (merges with existing).

    Args:
        user_id:     UUID of the user.
        preferences: Dict of key → value pairs to set.
        app_slug:    Namespace. None = "global".
    """
    if not preferences:
        return {"ok": False, "error": "preferences dict cannot be empty."}

    ns = _ns(app_slug)
    try:
        with get_conn() as conn:
            _ensure_preferences_row(conn, user_id)
            with dict_cursor(conn) as cur:
                # Merge the new preferences into the existing namespace
                cur.execute("""
                    UPDATE user_preferences
                    SET preferences = jsonb_set(
                        preferences,
                        ARRAY[%s],
                        COALESCE(preferences -> %s, '{}') || %s::jsonb,
                        true
                    ),
                    updated_at = NOW()
                    WHERE user_id = %s
                """, [ns, ns, json.dumps(preferences), user_id])

        return {
            "ok": True,
            "user_id": user_id,
            "namespace": ns,
            "keys_set": list(preferences.keys()),
        }
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_delete_preference(
    user_id: str,
    key: str,
    app_slug: str | None = None,
) -> dict[str, Any]:
    """
    Delete a single preference key.

    Args:
        user_id:  UUID of the user.
        key:      Preference key to delete.
        app_slug: Namespace. None = "global".
    """
    ns = _ns(app_slug)
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    UPDATE user_preferences
                    SET preferences = jsonb_set(
                        preferences,
                        ARRAY[%s],
                        (preferences -> %s) - %s,
                        false
                    ),
                    updated_at = NOW()
                    WHERE user_id = %s
                """, [ns, ns, key, user_id])

        return {"ok": True, "user_id": user_id, "namespace": ns, "deleted_key": key}
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}
