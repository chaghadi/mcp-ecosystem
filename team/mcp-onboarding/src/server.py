"""server.py — mcp-onboarding MCP server entry point.

Onboarding templates and assignments. Define a template once
(with steps), assign to new hires, track progress.
"""

import subprocess
import uuid
from datetime import datetime, timezone
from typing import Any

import psycopg2

from mcp.server.fastmcp import FastMCP
from src.config import settings
from src.db import dict_cursor, get_conn

mcp = FastMCP(
    "mcp-onboarding",
    instructions="Onboarding MCP for mmiri28 solutions. Define onboarding templates with steps, assign to new hires, track completion progress.",
)


@mcp.tool()
def health_check() -> dict:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM onboarding_templates")
                templates = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM onboardings WHERE status = 'active'")
                active = cur.fetchone()[0]
        return {"ok": True, "templates": templates, "active_onboardings": active}
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
def create_template(
    name: str, app_slug: str, role: str,
    steps: list[dict], description: str = "",
) -> dict[str, Any]:
    """
    Create an onboarding template.

    Args:
        name:        Template name (e.g. "Engineering — Backend").
        app_slug:    App/team slug.
        role:        Job role (e.g. "engineer", "designer", "pm").
        steps:       List of step dicts:
                     [{"title": "...", "description": "...", "day": 1, "required": true}]
        description: Optional template description.
    """
    if not steps:
        return {"ok": False, "error": "Template must have at least one step."}

    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                template_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO onboarding_templates
                        (id, name, app_slug, role, description, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, [template_id, name, app_slug, role, description,
                      datetime.now(timezone.utc)])

                for i, step in enumerate(steps):
                    step_id = str(uuid.uuid4())
                    cur.execute("""
                        INSERT INTO onboarding_template_steps
                            (id, template_id, step_order, title, description,
                             day_offset, required)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, [step_id, template_id, i + 1,
                          step.get("title", f"Step {i+1}"),
                          step.get("description", ""),
                          step.get("day", 1),
                          step.get("required", True)])

        return {"ok": True, "template_id": template_id, "name": name,
                "step_count": len(steps)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def start_onboarding(
    template_id: str, user_id: str, user_name: str,
    start_date: str | None = None,
) -> dict[str, Any]:
    """
    Start an onboarding for a new team member from a template.

    Args:
        template_id: Template UUID.
        user_id:     New hire's UUID/email/username.
        user_name:   New hire's name (for display).
        start_date:  ISO date (default: today).
    """
    try:
        from datetime import date
        target_date = datetime.fromisoformat(start_date).date() if start_date else date.today()
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("SELECT app_slug, name FROM onboarding_templates WHERE id = %s",
                            [template_id])
                template = cur.fetchone()
                if not template:
                    return {"ok": False, "error": "Template not found"}

                onboarding_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO onboardings
                        (id, template_id, user_id, user_name, app_slug,
                         start_date, status, started_at)
                    VALUES (%s, %s, %s, %s, %s, %s, 'active', %s)
                """, [onboarding_id, template_id, user_id, user_name,
                      template["app_slug"], target_date,
                      datetime.now(timezone.utc)])

                # Count steps for response
                cur.execute("""
                    SELECT COUNT(*) AS count FROM onboarding_template_steps
                    WHERE template_id = %s
                """, [template_id])
                step_count = cur.fetchone()["count"]

        return {"ok": True, "onboarding_id": onboarding_id,
                "template": template["name"], "user_name": user_name,
                "start_date": str(target_date), "total_steps": step_count}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def complete_step(
    onboarding_id: str, step_id: str, notes: str = "",
) -> dict[str, Any]:
    """Mark a step as complete for an onboarding."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                completion_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO onboarding_step_completions
                        (id, onboarding_id, step_id, notes, completed_at)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (onboarding_id, step_id) DO UPDATE SET
                        notes = EXCLUDED.notes, completed_at = EXCLUDED.completed_at
                """, [completion_id, onboarding_id, step_id, notes,
                      datetime.now(timezone.utc)])
        return {"ok": True, "onboarding_id": onboarding_id, "step_id": step_id}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def get_onboarding_progress(onboarding_id: str) -> dict[str, Any]:
    """Get progress for an onboarding — all steps with completion status."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    SELECT o.*, t.name AS template_name
                    FROM onboardings o
                    JOIN onboarding_templates t ON t.id = o.template_id
                    WHERE o.id = %s
                """, [onboarding_id])
                onboarding = cur.fetchone()
                if not onboarding:
                    return {"ok": False, "error": "Onboarding not found"}

                cur.execute("""
                    SELECT s.id, s.title, s.description, s.day_offset, s.required,
                           s.step_order, c.completed_at, c.notes
                    FROM onboarding_template_steps s
                    LEFT JOIN onboarding_step_completions c
                        ON c.step_id = s.id AND c.onboarding_id = %s
                    WHERE s.template_id = %s
                    ORDER BY s.step_order
                """, [onboarding_id, onboarding["template_id"]])
                steps = [dict(r) for r in cur.fetchall()]

        completed = sum(1 for s in steps if s["completed_at"])
        return {
            "ok": True, "onboarding_id": onboarding_id,
            "user_name": onboarding["user_name"],
            "template": onboarding["template_name"],
            "status": onboarding["status"],
            "progress": f"{completed}/{len(steps)}",
            "percent_complete": round(completed / len(steps) * 100, 1) if steps else 0,
            "steps": steps,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def list_active_onboardings(app_slug: str | None = None) -> dict[str, Any]:
    """List all active onboardings."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                where = "o.status = 'active'"
                params: list = []
                if app_slug:
                    where += " AND o.app_slug = %s"; params.append(app_slug)
                cur.execute(f"""
                    SELECT o.id, o.user_name, o.app_slug, o.start_date,
                           t.name AS template_name,
                           (SELECT COUNT(*) FROM onboarding_step_completions
                            WHERE onboarding_id = o.id) AS completed_steps,
                           (SELECT COUNT(*) FROM onboarding_template_steps
                            WHERE template_id = o.template_id) AS total_steps
                    FROM onboardings o
                    JOIN onboarding_templates t ON t.id = o.template_id
                    WHERE {where} ORDER BY o.start_date DESC
                """, params)
                onboardings = [dict(r) for r in cur.fetchall()]
        return {"ok": True, "count": len(onboardings), "onboardings": onboardings}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def complete_onboarding(onboarding_id: str) -> dict[str, Any]:
    """Mark an entire onboarding as completed."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    UPDATE onboardings
                    SET status = 'completed', completed_at = NOW()
                    WHERE id = %s RETURNING user_name
                """, [onboarding_id])
                row = cur.fetchone()
                if not row:
                    return {"ok": False, "error": "Onboarding not found"}
        return {"ok": True, "onboarding_id": onboarding_id,
                "user_name": row["user_name"], "status": "completed"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
