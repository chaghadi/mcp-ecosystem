"""server.py — mcp-analytics MCP server entry point."""

import subprocess
from mcp.server.fastmcp import FastMCP
from src.config import settings
from src.db import get_conn
from src.tools.analytics import (
    run_track_event, run_get_events, run_get_event_counts,
    run_get_funnel, run_get_user_stats,
)

mcp = FastMCP(
    "mcp-analytics",
    instructions=(
        "Analytics MCP for mmiri28 solutions. "
        "Postgres-based event tracking with funnel analysis and user stats. "
        "Zero vendor lock-in — all data in your own database."
    ),
)


@mcp.tool()
def health_check() -> dict:
    error = settings.validate()
    if error:
        return {"ok": False, "error": error}
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM events")
                count = cur.fetchone()[0]
        return {"ok": True, "status": "connected", "total_events": count}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def run_migrations() -> dict:
    """Create the events table."""
    error = settings.validate()
    if error:
        return {"ok": False, "error": error}
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        capture_output=True, text=True, cwd=str(settings.mcp_root),
    )
    if result.returncode != 0:
        return {"ok": False, "error": result.stderr or result.stdout}
    return {"ok": True, "output": result.stdout or "Migrations applied."}


@mcp.tool()
def track_event(
    app_slug: str,
    event_name: str,
    properties: dict | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
) -> dict:
    """
    Track a user event.

    Args:
        app_slug:   App that fired the event (e.g. "marketplace").
        event_name: Event name (e.g. "signup", "purchase", "page_view").
        properties: JSONB properties (e.g. {"plan": "pro", "amount": 9900}).
        user_id:    Optional user UUID. Null for anonymous events.
        session_id: Optional session identifier.
    """
    return run_track_event(app_slug=app_slug, event_name=event_name,
                           properties=properties, user_id=user_id, session_id=session_id)


@mcp.tool()
def get_events(
    app_slug: str,
    event_name: str | None = None,
    user_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 100,
) -> dict:
    """Query events with filters. Returns up to 1000 results."""
    return run_get_events(app_slug=app_slug, event_name=event_name, user_id=user_id,
                          start_date=start_date, end_date=end_date, limit=limit)


@mcp.tool()
def get_event_counts(
    app_slug: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Get event counts grouped by event name. Good for dashboards."""
    return run_get_event_counts(app_slug=app_slug, start_date=start_date, end_date=end_date)


@mcp.tool()
def get_funnel(
    app_slug: str,
    steps: list[str],
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """
    Calculate funnel conversion rates between ordered event steps.

    Args:
        app_slug: The app to analyse.
        steps:    Ordered event names (e.g. ["signup", "onboarding_done", "first_purchase"]).
    """
    return run_get_funnel(app_slug=app_slug, steps=steps,
                          start_date=start_date, end_date=end_date)


@mcp.tool()
def get_user_stats(user_id: str, app_slug: str | None = None) -> dict:
    """
    Get event statistics for a user — total events, top events, first/last seen.

    Args:
        user_id:  UUID of the user.
        app_slug: Filter to a specific app (optional).
    """
    return run_get_user_stats(user_id=user_id, app_slug=app_slug)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
