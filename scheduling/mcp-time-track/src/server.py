"""server.py — mcp-time-track MCP server entry point.

Time tracking: start/stop timers, log time entries, generate summaries.
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
    "mcp-time-track",
    instructions="Time tracking MCP for mmiri28 solutions. Start/stop timers, log time entries, generate daily/weekly summaries by app or category.",
)


@mcp.tool()
def health_check() -> dict:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM time_entries WHERE ended_at IS NULL")
                active = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM time_entries WHERE started_at::date = CURRENT_DATE")
                today = cur.fetchone()[0]
        return {"ok": True, "active_timers": active, "entries_today": today}
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
def start_timer(
    user_id: str, task: str, app_slug: str,
    category: str = "", notes: str = "",
) -> dict[str, Any]:
    """
    Start a timer. If one is already running for this user, it's stopped first.

    Args:
        user_id:  User identifier.
        task:     What you're working on.
        app_slug: Project/app context.
        category: Category like "coding", "meeting", "design".
        notes:    Free-form notes.
    """
    try:
        now = datetime.now(timezone.utc)
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                # Stop any running timer for this user
                cur.execute("""
                    UPDATE time_entries
                    SET ended_at = %s,
                        duration_seconds = EXTRACT(EPOCH FROM (%s - started_at))::INTEGER
                    WHERE user_id = %s AND ended_at IS NULL
                """, [now, now, user_id])

                # Start new
                entry_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO time_entries
                        (id, user_id, app_slug, task, category, notes, started_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, [entry_id, user_id, app_slug, task, category, notes, now])

        return {"ok": True, "entry_id": entry_id, "user_id": user_id,
                "task": task, "started_at": now.isoformat()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def stop_timer(user_id: str) -> dict[str, Any]:
    """Stop the currently running timer for a user."""
    try:
        now = datetime.now(timezone.utc)
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    UPDATE time_entries
                    SET ended_at = %s,
                        duration_seconds = EXTRACT(EPOCH FROM (%s - started_at))::INTEGER
                    WHERE user_id = %s AND ended_at IS NULL
                    RETURNING id, task, app_slug, duration_seconds
                """, [now, now, user_id])
                entry = cur.fetchone()
        if not entry:
            return {"ok": False, "error": "No timer running for this user."}
        mins = round(entry["duration_seconds"] / 60, 1)
        return {"ok": True, "entry_id": entry["id"], "task": entry["task"],
                "app_slug": entry["app_slug"],
                "duration_minutes": mins,
                "duration_seconds": entry["duration_seconds"]}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def log_time(
    user_id: str, task: str, app_slug: str,
    duration_minutes: int, category: str = "",
    notes: str = "", date_str: str | None = None,
) -> dict[str, Any]:
    """
    Manually log a completed time entry (without using a timer).

    Args:
        user_id:          User.
        task:             Task description.
        app_slug:         App context.
        duration_minutes: How long it took.
        category:         Optional category.
        notes:            Free-form notes.
        date_str:         ISO date (default: today).
    """
    try:
        target_date = datetime.fromisoformat(date_str).date() if date_str else date.today()
        started = datetime.combine(target_date, datetime.min.time(), timezone.utc)
        ended = started + timedelta(minutes=duration_minutes)
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                entry_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO time_entries
                        (id, user_id, app_slug, task, category, notes,
                         started_at, ended_at, duration_seconds)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [entry_id, user_id, app_slug, task, category, notes,
                      started, ended, duration_minutes * 60])
        return {"ok": True, "entry_id": entry_id, "duration_minutes": duration_minutes}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def get_current_timer(user_id: str) -> dict[str, Any]:
    """Get the currently running timer for a user."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    SELECT *, EXTRACT(EPOCH FROM (NOW() - started_at))::INTEGER AS elapsed_seconds
                    FROM time_entries
                    WHERE user_id = %s AND ended_at IS NULL
                """, [user_id])
                entry = cur.fetchone()
        if not entry:
            return {"ok": True, "running": False, "message": "No timer running."}
        d = dict(entry)
        d["elapsed_minutes"] = round(d["elapsed_seconds"] / 60, 1)
        return {"ok": True, "running": True, "timer": d}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def get_summary(
    user_id: str, days_back: int = 7,
    app_slug: str | None = None,
) -> dict[str, Any]:
    """
    Time summary for a user over the past N days.

    Returns totals by app, by category, and by day.

    Args:
        user_id:   User to summarise.
        days_back: How many days back (default: 7).
        app_slug:  Filter to one app (optional).
    """
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        conditions = ["user_id = %s", "ended_at IS NOT NULL", "started_at >= %s"]
        params: list = [user_id, cutoff]
        if app_slug:
            conditions.append("app_slug = %s"); params.append(app_slug)
        where = " AND ".join(conditions)

        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                # Totals
                cur.execute(f"""
                    SELECT COALESCE(SUM(duration_seconds), 0) AS total_seconds,
                           COUNT(*) AS entry_count
                    FROM time_entries WHERE {where}
                """, params)
                totals = dict(cur.fetchone())

                # By app
                cur.execute(f"""
                    SELECT app_slug, SUM(duration_seconds) AS seconds
                    FROM time_entries WHERE {where}
                    GROUP BY app_slug ORDER BY seconds DESC
                """, params)
                by_app = [dict(r) for r in cur.fetchall()]

                # By category
                cur.execute(f"""
                    SELECT category, SUM(duration_seconds) AS seconds
                    FROM time_entries WHERE {where} AND category != ''
                    GROUP BY category ORDER BY seconds DESC
                """, params)
                by_category = [dict(r) for r in cur.fetchall()]

                # By day
                cur.execute(f"""
                    SELECT started_at::date AS day, SUM(duration_seconds) AS seconds
                    FROM time_entries WHERE {where}
                    GROUP BY day ORDER BY day DESC
                """, params)
                by_day = [dict(r) for r in cur.fetchall()]

        return {
            "ok": True,
            "user_id": user_id, "period_days": days_back,
            "total_hours": round(totals["total_seconds"] / 3600, 2),
            "entry_count": totals["entry_count"],
            "by_app":      [{"app": r["app_slug"], "hours": round(r["seconds"]/3600, 2)} for r in by_app],
            "by_category": [{"category": r["category"], "hours": round(r["seconds"]/3600, 2)} for r in by_category],
            "by_day":      [{"day": str(r["day"]), "hours": round(r["seconds"]/3600, 2)} for r in by_day],
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def list_entries(
    user_id: str, days_back: int = 7,
    app_slug: str | None = None, limit: int = 50,
) -> dict[str, Any]:
    """List recent time entries for a user."""
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        conditions = ["user_id = %s", "started_at >= %s"]
        params: list = [user_id, cutoff]
        if app_slug:
            conditions.append("app_slug = %s"); params.append(app_slug)
        where = " AND ".join(conditions)
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute(f"""
                    SELECT * FROM time_entries WHERE {where}
                    ORDER BY started_at DESC LIMIT %s
                """, params + [min(limit, 200)])
                entries = [dict(e) for e in cur.fetchall()]
        return {"ok": True, "count": len(entries), "entries": entries}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
