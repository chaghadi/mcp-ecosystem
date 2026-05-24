"""server.py — mcp-cron MCP server entry point.

Cron-like job scheduling stored in Postgres.
Register schedules, find due jobs, log execution history.
The actual execution is delegated to the caller (e.g. a system cron task
that calls `get_due_jobs()` every minute and runs them).
"""

import json
import subprocess
import uuid
from datetime import datetime, timezone
from typing import Any

import psycopg2
from croniter import croniter

from mcp.server.fastmcp import FastMCP
from src.config import settings
from src.db import dict_cursor, get_conn

mcp = FastMCP(
    "mcp-cron",
    instructions="Cron scheduling MCP for mmiri28 solutions. Register jobs with cron expressions, find due jobs, log execution history. Designed to be polled by a system cron task.",
)


def _next_run(cron_expr: str, base: datetime | None = None) -> datetime:
    """Calculate next run time from cron expression."""
    base = base or datetime.now(timezone.utc)
    return croniter(cron_expr, base).get_next(datetime)


@mcp.tool()
def health_check() -> dict:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM cron_jobs WHERE is_active = true")
                active = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM cron_jobs WHERE next_run < NOW() AND is_active = true")
                due = cur.fetchone()[0]
        return {"ok": True, "active_jobs": active, "currently_due": due}
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
def register_job(
    name: str,
    cron_expression: str,
    action_type: str,
    action_payload: dict,
    app_slug: str = "system",
    description: str = "",
) -> dict[str, Any]:
    """
    Register a scheduled job.

    Args:
        name:            Unique job name (e.g. "daily-database-backup").
        cron_expression: Standard cron (e.g. "0 3 * * *" = 3am daily).
        action_type:     What kind of action (e.g. "mcp_tool", "http_call", "shell").
        action_payload:  Action details — caller interprets this.
                         Example: {"mcp": "mcp-backup", "tool": "backup_database", "args": {}}
        app_slug:        App that owns this job.
        description:     Human-readable description.
    """
    # Validate cron expression
    if not croniter.is_valid(cron_expression):
        return {"ok": False, "error": f"Invalid cron expression: {cron_expression}"}

    try:
        next_run = _next_run(cron_expression)
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                job_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO cron_jobs
                        (id, name, cron_expression, action_type, action_payload,
                         app_slug, description, next_run, is_active, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, true, %s)
                """, [job_id, name, cron_expression, action_type,
                      psycopg2.extras.Json(action_payload),
                      app_slug, description, next_run,
                      datetime.now(timezone.utc)])
        return {
            "ok": True, "job_id": job_id, "name": name,
            "cron_expression": cron_expression,
            "next_run": next_run.isoformat(),
        }
    except psycopg2.IntegrityError:
        return {"ok": False, "error": f"Job '{name}' already exists."}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def get_due_jobs() -> dict[str, Any]:
    """
    Return all active jobs whose next_run is in the past.
    The caller is responsible for executing the actions and calling
    record_execution() afterwards.
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    SELECT id, name, cron_expression, action_type, action_payload,
                           app_slug, last_run, next_run
                    FROM cron_jobs
                    WHERE is_active = true AND next_run < NOW()
                    ORDER BY next_run ASC
                """)
                jobs = [dict(r) for r in cur.fetchall()]
        return {"ok": True, "due_count": len(jobs), "jobs": jobs}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def record_execution(
    job_id: str, status: str = "success",
    output: str = "", error: str = "",
) -> dict[str, Any]:
    """
    Record that a job was executed and update its next_run time.

    Args:
        job_id:  The job that was run.
        status:  "success" | "failed" | "timeout"
        output:  Execution output (truncated to 2000 chars).
        error:   Error message if failed.
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("SELECT cron_expression FROM cron_jobs WHERE id = %s", [job_id])
                row = cur.fetchone()
                if not row:
                    return {"ok": False, "error": "Job not found"}

                next_run = _next_run(row["cron_expression"])
                now = datetime.now(timezone.utc)

                cur.execute("""
                    UPDATE cron_jobs
                    SET last_run = %s, next_run = %s
                    WHERE id = %s
                """, [now, next_run, job_id])

                exec_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO cron_executions
                        (id, job_id, status, output, error_message, executed_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, [exec_id, job_id, status, output[:2000], error[:2000], now])

        return {"ok": True, "job_id": job_id, "execution_id": exec_id,
                "next_run": next_run.isoformat()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def list_jobs(app_slug: str | None = None, active_only: bool = True) -> dict[str, Any]:
    """List registered jobs."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                conditions = []
                params: list = []
                if app_slug:
                    conditions.append("app_slug = %s")
                    params.append(app_slug)
                if active_only:
                    conditions.append("is_active = true")
                where = "WHERE " + " AND ".join(conditions) if conditions else ""
                cur.execute(f"SELECT * FROM cron_jobs {where} ORDER BY next_run", params)
                jobs = [dict(r) for r in cur.fetchall()]
        return {"ok": True, "count": len(jobs), "jobs": jobs}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def get_job_history(job_id: str, limit: int = 20) -> dict[str, Any]:
    """Get execution history for a job."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    SELECT * FROM cron_executions
                    WHERE job_id = %s ORDER BY executed_at DESC LIMIT %s
                """, [job_id, min(limit, 100)])
                history = [dict(r) for r in cur.fetchall()]
        return {"ok": True, "job_id": job_id, "count": len(history), "history": history}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def pause_job(job_id: str) -> dict[str, Any]:
    """Temporarily disable a job (won't appear in get_due_jobs)."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("UPDATE cron_jobs SET is_active = false WHERE id = %s", [job_id])
                paused = cur.rowcount > 0
        return {"ok": True, "paused": paused, "job_id": job_id}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def resume_job(job_id: str) -> dict[str, Any]:
    """Re-enable a paused job and reset its next_run."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("SELECT cron_expression FROM cron_jobs WHERE id = %s", [job_id])
                row = cur.fetchone()
                if not row:
                    return {"ok": False, "error": "Job not found"}
                next_run = _next_run(row["cron_expression"])
                cur.execute("UPDATE cron_jobs SET is_active = true, next_run = %s WHERE id = %s",
                            [next_run, job_id])
        return {"ok": True, "resumed": True, "next_run": next_run.isoformat()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def delete_job(job_id: str) -> dict[str, Any]:
    """Permanently delete a job and its history."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("DELETE FROM cron_jobs WHERE id = %s", [job_id])
                removed = cur.rowcount > 0
        return {"ok": True, "deleted": removed, "job_id": job_id}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
