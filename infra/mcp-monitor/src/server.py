"""server.py — mcp-monitor MCP server entry point.

Simple uptime monitoring backed by Postgres.
Register endpoints, run checks, view history.
Designed to be called by a cron schedule (mcp-cron) or manually.
"""

import subprocess
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import psycopg2

from mcp.server.fastmcp import FastMCP
from src.config import settings
from src.db import dict_cursor, get_conn

mcp = FastMCP(
    "mcp-monitor",
    instructions="Uptime monitoring MCP for mmiri28 solutions. Register endpoints, run HTTP checks, store results, calculate uptime percentages.",
)


@mcp.tool()
def health_check() -> dict:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM monitored_endpoints")
                endpoints = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM endpoint_checks WHERE created_at > NOW() - INTERVAL '24 hours'")
                checks_24h = cur.fetchone()[0]
        return {"ok": True, "status": "connected",
                "monitored_endpoints": endpoints, "checks_last_24h": checks_24h}
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
def register_endpoint(
    url: str, name: str, app_slug: str,
    check_interval_minutes: int = 5,
    expected_status: int = 200,
    timeout_seconds: int = 10,
) -> dict:
    """
    Register an endpoint for uptime monitoring.

    Args:
        url:                    Full HTTPS URL to monitor.
        name:                   Human-readable label.
        app_slug:               App this endpoint belongs to.
        check_interval_minutes: How often to check. Default: 5.
        expected_status:        Expected HTTP status. Default: 200.
        timeout_seconds:        Request timeout. Default: 10.
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                endpoint_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO monitored_endpoints
                        (id, url, name, app_slug, check_interval_minutes,
                         expected_status, timeout_seconds, is_active, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, true, %s)
                """, [endpoint_id, url, name, app_slug,
                      check_interval_minutes, expected_status,
                      timeout_seconds, datetime.now(timezone.utc)])
        return {"ok": True, "endpoint_id": endpoint_id, "name": name, "url": url}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def check_endpoint(endpoint_id: str) -> dict[str, Any]:
    """
    Run a single check against a registered endpoint.

    Args:
        endpoint_id: UUID of the endpoint.
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("SELECT * FROM monitored_endpoints WHERE id = %s", [endpoint_id])
                endpoint = cur.fetchone()

        if not endpoint:
            return {"ok": False, "error": f"Endpoint '{endpoint_id}' not found"}

        # Run the check
        start = datetime.now(timezone.utc)
        check_status = "down"
        status_code = None
        error_message = ""
        try:
            r = httpx.get(endpoint["url"], timeout=endpoint["timeout_seconds"],
                          follow_redirects=True)
            status_code = r.status_code
            if status_code == endpoint["expected_status"]:
                check_status = "up"
            else:
                check_status = "degraded"
                error_message = f"Expected {endpoint['expected_status']}, got {status_code}"
        except httpx.TimeoutException:
            error_message = "Request timed out"
        except Exception as exc:
            error_message = str(exc)

        duration_ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)

        # Record the check
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                check_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO endpoint_checks
                        (id, endpoint_id, status, status_code, duration_ms,
                         error_message, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, [check_id, endpoint_id, check_status, status_code,
                      duration_ms, error_message, datetime.now(timezone.utc)])

        return {
            "ok": True, "endpoint_id": endpoint_id,
            "url": endpoint["url"], "name": endpoint["name"],
            "status": check_status, "status_code": status_code,
            "duration_ms": duration_ms, "error": error_message or None,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def check_all_due() -> dict[str, Any]:
    """
    Check all endpoints that are due (interval has elapsed since last check).
    Designed to be called by a cron-like scheduler.
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    SELECT me.id, me.url, me.name,
                           COALESCE(MAX(ec.created_at), '1970-01-01'::timestamptz) AS last_check,
                           me.check_interval_minutes
                    FROM monitored_endpoints me
                    LEFT JOIN endpoint_checks ec ON ec.endpoint_id = me.id
                    WHERE me.is_active = true
                    GROUP BY me.id, me.url, me.name, me.check_interval_minutes
                """)
                endpoints = cur.fetchall()

        now = datetime.now(timezone.utc)
        due_endpoints = []
        for e in endpoints:
            elapsed_min = (now - e["last_check"]).total_seconds() / 60
            if elapsed_min >= e["check_interval_minutes"]:
                due_endpoints.append(e)

        results = []
        for e in due_endpoints:
            r = check_endpoint(e["id"])
            if r["ok"]:
                results.append({"name": e["name"], "status": r["status"],
                                "duration_ms": r["duration_ms"]})

        return {
            "ok": True, "total_endpoints": len(endpoints),
            "checked_now": len(results), "results": results,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def get_status(endpoint_id: str) -> dict[str, Any]:
    """
    Get the current status and uptime percentage for an endpoint.
    Includes uptime over the last 24 hours, 7 days, and 30 days.
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    SELECT me.*,
                           (SELECT row_to_json(c.*) FROM (
                               SELECT status, status_code, duration_ms, error_message, created_at
                               FROM endpoint_checks
                               WHERE endpoint_id = me.id
                               ORDER BY created_at DESC LIMIT 1
                           ) c) AS last_check
                    FROM monitored_endpoints me WHERE me.id = %s
                """, [endpoint_id])
                e = cur.fetchone()
                if not e:
                    return {"ok": False, "error": "Endpoint not found"}

                # Uptime percentages
                cur.execute("""
                    SELECT
                        AVG(CASE WHEN status = 'up' THEN 100.0 ELSE 0 END) FILTER
                            (WHERE created_at > NOW() - INTERVAL '24 hours') AS uptime_24h,
                        AVG(CASE WHEN status = 'up' THEN 100.0 ELSE 0 END) FILTER
                            (WHERE created_at > NOW() - INTERVAL '7 days') AS uptime_7d,
                        AVG(CASE WHEN status = 'up' THEN 100.0 ELSE 0 END) FILTER
                            (WHERE created_at > NOW() - INTERVAL '30 days') AS uptime_30d
                    FROM endpoint_checks WHERE endpoint_id = %s
                """, [endpoint_id])
                uptime = cur.fetchone()

        return {
            "ok": True,
            "endpoint_id": endpoint_id,
            "name": e["name"], "url": e["url"],
            "current": e["last_check"],
            "uptime_24h": round(uptime["uptime_24h"] or 0, 2),
            "uptime_7d":  round(uptime["uptime_7d"]  or 0, 2),
            "uptime_30d": round(uptime["uptime_30d"] or 0, 2),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def list_endpoints(app_slug: str | None = None) -> dict[str, Any]:
    """List all registered endpoints, optionally filtered by app."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                if app_slug:
                    cur.execute("SELECT * FROM monitored_endpoints WHERE app_slug = %s ORDER BY name", [app_slug])
                else:
                    cur.execute("SELECT * FROM monitored_endpoints ORDER BY app_slug, name")
                endpoints = [dict(e) for e in cur.fetchall()]
        return {"ok": True, "count": len(endpoints), "endpoints": endpoints}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def delete_endpoint(endpoint_id: str) -> dict[str, Any]:
    """Remove an endpoint from monitoring (and all its check history)."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("DELETE FROM monitored_endpoints WHERE id = %s", [endpoint_id])
                removed = cur.rowcount > 0
        return {"ok": True, "removed": removed, "endpoint_id": endpoint_id}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
