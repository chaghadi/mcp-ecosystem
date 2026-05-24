"""
roles.py — App and role management tools.

create_app()      — register an app in the ecosystem
create_role()     — define a role for an app
assign_role()     — assign a role to a user in an app
revoke_role()     — remove a role from a user in an app
get_user_roles()  — get all roles for a user in an app
list_app_roles()  — list all defined roles for an app
"""

import uuid
from datetime import datetime, timezone
from typing import Any

import psycopg2

from src.db import dict_cursor, get_conn


def run_create_app(slug: str, name: str) -> dict[str, Any]:
    """
    Register an app in the ecosystem.

    Apps must be registered before roles can be defined for them.
    The slug is used as the app identifier in tokens and role assignments.

    Args:
        slug: URL-safe identifier (e.g. "marketplace", "saas-tool").
        name: Human-readable name (e.g. "mmiri28 Marketplace").
    """
    slug = slug.strip().lower().replace(" ", "-")
    if not slug:
        return {"ok": False, "error": "slug cannot be empty."}

    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("SELECT id FROM apps WHERE slug = %s", [slug])
                if cur.fetchone():
                    return {"ok": False, "error": f"App '{slug}' already exists."}

                app_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO apps (id, slug, name, is_active, created_at)
                    VALUES (%s, %s, %s, true, %s)
                """, [app_id, slug, name.strip(), datetime.now(timezone.utc)])

        return {"ok": True, "app_id": app_id, "slug": slug, "name": name}
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_create_role(
    app_slug: str,
    role_name: str,
    description: str = "",
) -> dict[str, Any]:
    """
    Define a role for an app.

    Args:
        app_slug:    The app this role belongs to.
        role_name:   Role identifier (e.g. "seller", "buyer", "moderator").
        description: Optional human-readable description.
    """
    role_name = role_name.strip().lower().replace(" ", "_")
    if not role_name:
        return {"ok": False, "error": "role_name cannot be empty."}

    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("SELECT id FROM apps WHERE slug = %s", [app_slug])
                app = cur.fetchone()
                if not app:
                    return {"ok": False, "error": f"App '{app_slug}' not found. Run create_app first."}

                cur.execute(
                    "SELECT id FROM app_roles WHERE app_id = %s AND name = %s",
                    [app["id"], role_name]
                )
                if cur.fetchone():
                    return {"ok": False, "error": f"Role '{role_name}' already exists in '{app_slug}'."}

                role_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO app_roles (id, app_id, name, description, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, [role_id, app["id"], role_name, description, datetime.now(timezone.utc)])

        return {"ok": True, "role_id": role_id, "app_slug": app_slug, "role_name": role_name}
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_assign_role(
    user_id: str,
    app_slug: str,
    role_name: str,
    assigned_by_user_id: str | None = None,
) -> dict[str, Any]:
    """
    Assign a role to a user in an app.

    Args:
        user_id:              The user to assign the role to.
        app_slug:             The app context.
        role_name:            The role to assign.
        assigned_by_user_id:  Who is making the assignment (for audit).
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("SELECT id FROM users WHERE id = %s", [user_id])
                if not cur.fetchone():
                    return {"ok": False, "error": f"User '{user_id}' not found."}

                cur.execute("""
                    SELECT ar.id FROM app_roles ar
                    JOIN apps a ON a.id = ar.app_id
                    WHERE a.slug = %s AND ar.name = %s
                """, [app_slug, role_name])
                role = cur.fetchone()
                if not role:
                    return {"ok": False, "error": f"Role '{role_name}' not found in app '{app_slug}'."}

                cur.execute("SELECT id FROM apps WHERE slug = %s", [app_slug])
                app = cur.fetchone()

                cur.execute("""
                    INSERT INTO user_app_roles (id, user_id, app_id, role_id, assigned_at, assigned_by)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, app_id, role_id) DO NOTHING
                """, [
                    str(uuid.uuid4()), user_id, app["id"], role["id"],
                    datetime.now(timezone.utc), assigned_by_user_id
                ])

        return {
            "ok": True,
            "user_id": user_id,
            "app_slug": app_slug,
            "role_name": role_name,
            "assigned_by": assigned_by_user_id,
        }
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_revoke_role(
    user_id: str,
    app_slug: str,
    role_name: str,
) -> dict[str, Any]:
    """
    Remove a role from a user in an app.

    Args:
        user_id:   The user.
        app_slug:  The app context.
        role_name: The role to remove.
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    DELETE FROM user_app_roles
                    WHERE user_id = %s
                      AND app_id = (SELECT id FROM apps WHERE slug = %s)
                      AND role_id = (
                          SELECT ar.id FROM app_roles ar
                          JOIN apps a ON a.id = ar.app_id
                          WHERE a.slug = %s AND ar.name = %s
                      )
                """, [user_id, app_slug, app_slug, role_name])
                removed = cur.rowcount > 0

        return {
            "ok": True,
            "removed": removed,
            "user_id": user_id,
            "app_slug": app_slug,
            "role_name": role_name,
        }
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_get_user_roles(user_id: str, app_slug: str | None = None) -> dict[str, Any]:
    """
    Get all roles for a user, optionally filtered to one app.

    Args:
        user_id:  The user.
        app_slug: Optional — filter to a specific app.
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                if app_slug:
                    cur.execute("""
                        SELECT ar.name AS role, a.slug AS app
                        FROM user_app_roles uar
                        JOIN apps a ON a.id = uar.app_id
                        JOIN app_roles ar ON ar.id = uar.role_id
                        WHERE uar.user_id = %s AND a.slug = %s
                        ORDER BY ar.name
                    """, [user_id, app_slug])
                else:
                    cur.execute("""
                        SELECT ar.name AS role, a.slug AS app
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

        return {
            "ok": True,
            "user_id": user_id,
            "app_slug": app_slug,
            "roles": [{"app": app, "roles": roles} for app, roles in grouped.items()],
        }
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_list_app_roles(app_slug: str) -> dict[str, Any]:
    """
    List all defined roles for an app.

    Args:
        app_slug: The app to list roles for.
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    SELECT ar.id, ar.name, ar.description, ar.created_at
                    FROM app_roles ar
                    JOIN apps a ON a.id = ar.app_id
                    WHERE a.slug = %s
                    ORDER BY ar.name
                """, [app_slug])
                roles = [dict(r) for r in cur.fetchall()]

        return {
            "ok": True,
            "app_slug": app_slug,
            "role_count": len(roles),
            "roles": roles,
        }
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}
