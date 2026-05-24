"""analytics.py — Event tracking and analysis tools."""

import uuid
from datetime import datetime, timezone
from typing import Any

import psycopg2

from src.db import dict_cursor, get_conn


def run_track_event(
    app_slug: str,
    event_name: str,
    properties: dict | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """
    Track an event. Called by apps to record user actions.

    Args:
        app_slug:   Which app fired the event.
        event_name: Event identifier (e.g. "signup", "purchase", "page_view").
        properties: Arbitrary JSONB data about the event.
        user_id:    Optional UUID — null for anonymous events.
        session_id: Optional session identifier.
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                event_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO events (id, user_id, app_slug, event_name, properties, session_id, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, [event_id, user_id, app_slug, event_name,
                      psycopg2.extras.Json(properties or {}),
                      session_id, datetime.now(timezone.utc)])
        return {"ok": True, "event_id": event_id, "event_name": event_name, "app_slug": app_slug}
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_get_events(
    app_slug: str,
    event_name: str | None = None,
    user_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """
    Query events with filters.

    Args:
        app_slug:   Required — which app's events.
        event_name: Filter to a specific event.
        user_id:    Filter to a specific user.
        start_date: ISO date string (e.g. "2026-01-01").
        end_date:   ISO date string.
        limit:      Max results. Default 100. Max 1000.
    """
    limit = min(max(1, limit), 1000)
    conditions = ["app_slug = %s"]
    params: list = [app_slug]

    if event_name:
        conditions.append("event_name = %s")
        params.append(event_name)
    if user_id:
        conditions.append("user_id = %s")
        params.append(user_id)
    if start_date:
        conditions.append("created_at >= %s")
        params.append(start_date)
    if end_date:
        conditions.append("created_at <= %s")
        params.append(end_date)

    where = " AND ".join(conditions)
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute(
                    f"SELECT * FROM events WHERE {where} ORDER BY created_at DESC LIMIT %s",
                    params + [limit]
                )
                events = [dict(r) for r in cur.fetchall()]
        return {"ok": True, "app_slug": app_slug, "count": len(events), "events": events}
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_get_event_counts(
    app_slug: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """
    Get event counts grouped by event name for an app.

    Useful for building dashboards showing top events.
    """
    conditions = ["app_slug = %s"]
    params: list = [app_slug]
    if start_date:
        conditions.append("created_at >= %s")
        params.append(start_date)
    if end_date:
        conditions.append("created_at <= %s")
        params.append(end_date)
    where = " AND ".join(conditions)

    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute(f"""
                    SELECT event_name,
                           COUNT(*) AS total,
                           COUNT(DISTINCT user_id) AS unique_users
                    FROM events WHERE {where}
                    GROUP BY event_name ORDER BY total DESC
                """, params)
                counts = [dict(r) for r in cur.fetchall()]
        return {"ok": True, "app_slug": app_slug, "event_counts": counts}
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_get_funnel(
    app_slug: str,
    steps: list[str],
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """
    Calculate funnel conversion rates between ordered event steps.

    Args:
        app_slug:   The app to analyse.
        steps:      Ordered list of event names (e.g. ["signup", "onboarding_complete", "first_purchase"]).
        start_date: ISO date string.
        end_date:   ISO date string.
    """
    if len(steps) < 2:
        return {"ok": False, "error": "steps must have at least 2 events."}

    conditions = "app_slug = %s"
    base_params: list = [app_slug]
    if start_date:
        conditions += " AND created_at >= %s"
        base_params.append(start_date)
    if end_date:
        conditions += " AND created_at <= %s"
        base_params.append(end_date)

    try:
        with get_conn() as conn:
            step_counts = []
            for step in steps:
                with dict_cursor(conn) as cur:
                    cur.execute(f"""
                        SELECT COUNT(DISTINCT user_id) AS users
                        FROM events
                        WHERE {conditions} AND event_name = %s AND user_id IS NOT NULL
                    """, base_params + [step])
                    count = cur.fetchone()["users"]
                    step_counts.append({"event": step, "users": count})

        # Calculate conversion rates
        funnel = []
        for i, step in enumerate(step_counts):
            prev = step_counts[i - 1]["users"] if i > 0 else step["users"]
            rate = round(step["users"] / prev * 100, 1) if prev > 0 else 0
            funnel.append({
                "step": i + 1,
                "event": step["event"],
                "users": step["users"],
                "conversion_from_previous": f"{rate}%",
                "conversion_from_start": f"{round(step['users'] / step_counts[0]['users'] * 100, 1)}%" if step_counts[0]["users"] > 0 else "0%",
            })

        return {"ok": True, "app_slug": app_slug, "funnel": funnel}
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_get_user_stats(user_id: str, app_slug: str | None = None) -> dict[str, Any]:
    """
    Get event statistics for a specific user.

    Args:
        user_id:  UUID of the user.
        app_slug: Filter to a specific app (optional).
    """
    conditions = "user_id = %s"
    params: list = [user_id]
    if app_slug:
        conditions += " AND app_slug = %s"
        params.append(app_slug)

    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute(f"""
                    SELECT
                        COUNT(*) AS total_events,
                        COUNT(DISTINCT event_name) AS unique_event_types,
                        COUNT(DISTINCT app_slug) AS apps_used,
                        MIN(created_at) AS first_seen,
                        MAX(created_at) AS last_seen
                    FROM events WHERE {conditions}
                """, params)
                stats = dict(cur.fetchone())

                cur.execute(f"""
                    SELECT event_name, COUNT(*) AS count
                    FROM events WHERE {conditions}
                    GROUP BY event_name ORDER BY count DESC LIMIT 10
                """, params)
                top_events = [dict(r) for r in cur.fetchall()]

        return {"ok": True, "user_id": user_id, "app_slug": app_slug,
                "stats": stats, "top_events": top_events}
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}
