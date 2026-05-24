"""server.py — mcp-standup MCP server entry point.

Async daily standups: what you did, what you're doing, blockers.
Per-app or per-team summaries.
"""

import subprocess
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

import psycopg2

from mcp.server.fastmcp import FastMCP
from src.config import settings
from src.db import dict_cursor, get_conn

mcp = FastMCP(
    "mcp-standup",
    instructions="Async standup MCP for mmiri28 solutions. Daily check-ins: yesterday, today, blockers. Per-app team summaries.",
)


@mcp.tool()
def health_check() -> dict:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM standups WHERE date = CURRENT_DATE")
                today = cur.fetchone()[0]
                cur.execute("SELECT COUNT(DISTINCT user_id) FROM standups WHERE date > CURRENT_DATE - 7")
                active_week = cur.fetchone()[0]
        return {"ok": True, "standups_today": today, "active_users_7d": active_week}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def run_migrations() -> dict:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        capture_output=True, text=True, cwd=str(settings.mcp_root),
    )
    if result.returncode != 0:
        return {"ok": False, "error": result.stderr or result.stdout}
    return {"ok": True, "output": result.stdout or "Migrations applied."}


@mcp.tool()
def submit_standup(
    user_id: str, app_slug: str,
    yesterday: str, today: str,
    blockers: str = "", mood: str = "",
) -> dict[str, Any]:
    """
    Submit today's standup. If one already exists today, it's updated.

    Args:
        user_id:   Submitter (UUID or username).
        app_slug:  App or team slug.
        yesterday: What you did yesterday.
        today:     What you're doing today.
        blockers:  Anything blocking you (optional).
        mood:      Optional mood/energy indicator (e.g. "🟢", "tired", "focused").
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                today_date = date.today()
                cur.execute("""
                    INSERT INTO standups
                        (id, user_id, app_slug, date, yesterday, today, blockers, mood, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, app_slug, date) DO UPDATE SET
                        yesterday = EXCLUDED.yesterday,
                        today     = EXCLUDED.today,
                        blockers  = EXCLUDED.blockers,
                        mood      = EXCLUDED.mood,
                        created_at = EXCLUDED.created_at
                    RETURNING id
                """, [str(uuid.uuid4()), user_id, app_slug, today_date,
                      yesterday, today, blockers, mood,
                      datetime.now(timezone.utc)])
                standup_id = cur.fetchone()["id"]
        return {"ok": True, "standup_id": standup_id, "user_id": user_id,
                "app_slug": app_slug, "date": today_date.isoformat(),
                "has_blockers": bool(blockers.strip())}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def get_standup(user_id: str, app_slug: str, date_str: str | None = None) -> dict[str, Any]:
    """Get a user's standup for a specific date (default: today)."""
    try:
        target_date = datetime.fromisoformat(date_str).date() if date_str else date.today()
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    SELECT * FROM standups
                    WHERE user_id = %s AND app_slug = %s AND date = %s
                """, [user_id, app_slug, target_date])
                standup = cur.fetchone()
        if not standup:
            return {"ok": False, "error": f"No standup for {user_id} on {target_date}"}
        return {"ok": True, "standup": dict(standup)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def list_standups(
    app_slug: str, days_back: int = 1, user_id: str | None = None,
) -> dict[str, Any]:
    """
    List standups for an app/team.

    Args:
        app_slug:  Team identifier.
        days_back: Look back this many days (0 = today only).
        user_id:   Filter to one user (optional).
    """
    try:
        cutoff = date.today() - timedelta(days=days_back)
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                conditions = ["app_slug = %s", "date >= %s"]
                params: list = [app_slug, cutoff]
                if user_id:
                    conditions.append("user_id = %s")
                    params.append(user_id)
                where = " AND ".join(conditions)
                cur.execute(f"""
                    SELECT * FROM standups WHERE {where}
                    ORDER BY date DESC, created_at DESC
                """, params)
                standups = [dict(s) for s in cur.fetchall()]
        return {"ok": True, "app_slug": app_slug, "count": len(standups),
                "standups": standups}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def get_team_summary(app_slug: str, date_str: str | None = None) -> dict[str, Any]:
    """
    Get a team summary for a specific day.
    Shows who checked in, who has blockers, and aggregated content.

    Args:
        app_slug: Team identifier.
        date_str: ISO date (default: today).
    """
    try:
        target_date = datetime.fromisoformat(date_str).date() if date_str else date.today()
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    SELECT user_id, yesterday, today, blockers, mood
                    FROM standups WHERE app_slug = %s AND date = %s
                    ORDER BY user_id
                """, [app_slug, target_date])
                standups = [dict(s) for s in cur.fetchall()]

        with_blockers = [s for s in standups if s["blockers"] and s["blockers"].strip()]

        return {
            "ok": True, "app_slug": app_slug,
            "date": target_date.isoformat(),
            "checkin_count": len(standups),
            "blocker_count": len(with_blockers),
            "blockers": [{"user": s["user_id"], "blocker": s["blockers"]}
                         for s in with_blockers],
            "team": [{"user": s["user_id"], "today": s["today"], "mood": s["mood"]}
                     for s in standups],
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
