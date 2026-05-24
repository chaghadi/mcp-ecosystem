"""
lifecycle.py — User lifecycle tools.

delete_user()       — hard delete, GDPR right to erasure
export_user_data()  — GDPR Article 20 data export
"""

import json
from datetime import datetime, timezone
from typing import Any

import psycopg2

from src.db import dict_cursor, get_conn


def run_delete_user(user_id: str, reason: str = "") -> dict[str, Any]:
    """
    Permanently delete a user and all their data (GDPR right to erasure).

    This is irreversible. Cascades to:
    - user_profiles, user_preferences
    - user_app_roles, refresh_tokens, oauth_accounts (via FK cascade)
    - users row

    Soft delete (deactivation) is handled by mcp-auth.
    Use this only for GDPR erasure requests.

    Args:
        user_id: UUID of the user to delete.
        reason:  Optional reason for audit purposes.
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                # Confirm user exists before deleting
                cur.execute(
                    "SELECT email, phone, username FROM users WHERE id = %s",
                    [user_id]
                )
                user = cur.fetchone()
                if not user:
                    return {"ok": False, "error": f"User '{user_id}' not found."}

                # Capture identifier for confirmation (anonymised)
                identifier = (
                    user["email"] or user["phone"] or user["username"] or "unknown"
                )

                # Delete — FK cascades handle all child tables
                cur.execute("DELETE FROM users WHERE id = %s", [user_id])

        return {
            "ok": True,
            "user_id": user_id,
            "identifier_hint": identifier[:3] + "***",
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "warning": "This deletion is permanent and cannot be undone.",
        }
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_export_user_data(user_id: str) -> dict[str, Any]:
    """
    Export all data held for a user (GDPR Article 20 — right to data portability).

    Returns a structured dict of all user data across all tables.
    Apps should format this as a downloadable JSON file for the user.

    Args:
        user_id: UUID of the user.
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                # Core identity
                cur.execute("""
                    SELECT id, email, phone, username, global_role,
                           is_active, is_verified, created_at, updated_at
                    FROM users WHERE id = %s
                """, [user_id])
                user = cur.fetchone()
                if not user:
                    return {"ok": False, "error": f"User '{user_id}' not found."}

                # Profile
                cur.execute(
                    "SELECT * FROM user_profiles WHERE user_id = %s", [user_id]
                )
                profile = cur.fetchone()

                # Preferences
                cur.execute(
                    "SELECT preferences, updated_at FROM user_preferences WHERE user_id = %s",
                    [user_id]
                )
                prefs = cur.fetchone()

                # App roles
                cur.execute("""
                    SELECT a.slug AS app, ar.name AS role, uar.assigned_at
                    FROM user_app_roles uar
                    JOIN apps a ON a.id = uar.app_id
                    JOIN app_roles ar ON ar.id = uar.role_id
                    WHERE uar.user_id = %s
                    ORDER BY a.slug, ar.name
                """, [user_id])
                roles = [dict(r) for r in cur.fetchall()]

        export = {
            "export_generated_at": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "account": dict(user),
            "profile": dict(profile) if profile else None,
            "preferences": dict(prefs) if prefs else None,
            "app_roles": roles,
        }

        return {
            "ok": True,
            "user_id": user_id,
            "export": export,
            "note": "Provide this data to the user as a downloadable JSON file.",
        }
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}
