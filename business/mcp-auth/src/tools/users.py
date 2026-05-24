"""
users.py — User management tools.

get_user()        — look up a user by id, email, phone, or username
update_user()     — update user fields
deactivate_user() — soft delete (sets is_active=false)
list_users()      — list users with optional app/role filter
"""

from datetime import datetime, timezone
from typing import Any

import psycopg2

from src.db import dict_cursor, get_conn


def _safe_user(row: dict) -> dict:
    """Return a user dict with password_hash removed."""
    return {k: v for k, v in row.items() if k != "password_hash"}


def run_get_user(identifier: str) -> dict[str, Any]:
    """
    Look up a user by UUID, email, phone, or username.

    Args:
        identifier: UUID, email address, phone number, or username.
    """
    identifier = identifier.strip()
    if not identifier:
        return {"ok": False, "error": "identifier cannot be empty."}

    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    SELECT id, email, phone, username, global_role,
                           is_active, is_verified, created_at, updated_at
                    FROM users
                    WHERE id = %s OR email = %s OR phone = %s OR username = %s
                    LIMIT 1
                """, [identifier, identifier, identifier, identifier])
                user = cur.fetchone()

        if not user:
            return {"ok": False, "error": f"User '{identifier}' not found."}

        return {"ok": True, "user": dict(user)}
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_update_user(user_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    """
    Update user fields.

    Allowed fields: email, phone, username, is_verified.
    password must be changed via a dedicated password reset flow (not here).
    global_role can only be changed by a superadmin via assign_global_role (not here).

    Args:
        user_id: UUID of the user to update.
        fields:  Dict of fields to update.
    """
    ALLOWED = {"email", "phone", "username", "is_verified"}
    updates = {k: v for k, v in fields.items() if k in ALLOWED}

    if not updates:
        return {
            "ok": False,
            "error": f"No valid fields to update. Allowed: {', '.join(ALLOWED)}",
        }

    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                set_clause = ", ".join(f"{k} = %s" for k in updates)
                values = list(updates.values()) + [datetime.now(timezone.utc), user_id]
                cur.execute(
                    f"UPDATE users SET {set_clause}, updated_at = %s WHERE id = %s RETURNING id",
                    values
                )
                if not cur.fetchone():
                    return {"ok": False, "error": f"User '{user_id}' not found."}

        return {"ok": True, "user_id": user_id, "updated_fields": list(updates.keys())}
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_deactivate_user(user_id: str) -> dict[str, Any]:
    """
    Deactivate a user account (soft delete).

    The user cannot log in after deactivation.
    Existing tokens remain valid until they expire or are blacklisted.

    Args:
        user_id: UUID of the user to deactivate.
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    UPDATE users SET is_active = false, updated_at = %s
                    WHERE id = %s RETURNING id
                """, [datetime.now(timezone.utc), user_id])
                if not cur.fetchone():
                    return {"ok": False, "error": f"User '{user_id}' not found."}

                # Revoke all refresh tokens
                cur.execute("""
                    UPDATE refresh_tokens SET revoked_at = NOW()
                    WHERE user_id = %s AND revoked_at IS NULL
                """, [user_id])

        return {
            "ok": True,
            "user_id": user_id,
            "deactivated": True,
            "note": "All refresh tokens revoked. Access tokens expire naturally.",
        }
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_list_users(
    app_slug: str | None = None,
    role_name: str | None = None,
    page: int = 1,
    limit: int = 50,
) -> dict[str, Any]:
    """
    List users with optional filtering by app and role.

    Args:
        app_slug:  Filter to users who have a role in this app.
        role_name: Filter to users who have this specific role.
        page:      Page number (1-based). Default: 1.
        limit:     Results per page. Default: 50. Max: 200.
    """
    limit = min(max(1, limit), 200)
    offset = (max(1, page) - 1) * limit

    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                if app_slug:
                    join_clause = """
                        JOIN user_app_roles uar ON uar.user_id = u.id
                        JOIN apps a ON a.id = uar.app_id AND a.slug = %s
                    """
                    params_base = [app_slug]
                    if role_name:
                        join_clause += " JOIN app_roles ar ON ar.id = uar.role_id AND ar.name = %s"
                        params_base.append(role_name)
                else:
                    join_clause = ""
                    params_base = []

                count_sql = f"SELECT COUNT(DISTINCT u.id) FROM users u {join_clause}"
                cur.execute(count_sql, params_base)
                total = cur.fetchone()["count"]

                list_sql = f"""
                    SELECT DISTINCT u.id, u.email, u.phone, u.username,
                           u.global_role, u.is_active, u.is_verified, u.created_at
                    FROM users u {join_clause}
                    ORDER BY u.created_at DESC
                    LIMIT %s OFFSET %s
                """
                cur.execute(list_sql, params_base + [limit, offset])
                users = [dict(r) for r in cur.fetchall()]

        return {
            "ok": True,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit,
            "users": users,
        }
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}
