"""search.py — User search tool."""

from typing import Any
import psycopg2
from src.db import dict_cursor, get_conn


def run_search_users(
    query: str,
    app_slug: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """
    Search users by display name, email, username, or phone.

    Args:
        query:    Search term (min 2 chars).
        app_slug: Restrict to users who have a role in this app.
        page:     Page number. Default: 1.
        limit:    Results per page. Default: 20. Max: 100.
    """
    query = query.strip()
    if len(query) < 2:
        return {"ok": False, "error": "query must be at least 2 characters."}

    limit = min(max(1, limit), 100)
    offset = (max(1, page) - 1) * limit
    pattern = f"%{query}%"

    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                app_join = ""
                app_params: list = []
                if app_slug:
                    app_join = """
                        JOIN user_app_roles uar ON uar.user_id = u.id
                        JOIN apps a ON a.id = uar.app_id AND a.slug = %s
                    """
                    app_params = [app_slug]

                sql = f"""
                    SELECT DISTINCT
                        u.id, u.email, u.phone, u.username,
                        u.global_role, u.is_active, u.is_verified,
                        p.display_name, p.avatar_url
                    FROM users u
                    LEFT JOIN user_profiles p ON p.user_id = u.id
                    {app_join}
                    WHERE u.is_active = true AND (
                        u.email    ILIKE %s OR
                        u.username ILIKE %s OR
                        u.phone    ILIKE %s OR
                        p.display_name ILIKE %s
                    )
                    ORDER BY p.display_name, u.email
                    LIMIT %s OFFSET %s
                """
                params = app_params + [pattern, pattern, pattern, pattern, limit, offset]
                cur.execute(sql, params)
                results = [dict(r) for r in cur.fetchall()]

        return {
            "ok": True,
            "query": query,
            "app_slug": app_slug,
            "result_count": len(results),
            "page": page,
            "limit": limit,
            "results": results,
        }
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}
