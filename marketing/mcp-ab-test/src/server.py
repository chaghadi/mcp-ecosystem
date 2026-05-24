"""server.py — mcp-ab-test MCP server entry point.

A/B testing framework with consistent variant assignment.
Same user gets the same variant via deterministic hashing.
"""

import hashlib
import subprocess
import uuid
from datetime import datetime, timezone
from typing import Any

import psycopg2

from mcp.server.fastmcp import FastMCP
from src.config import settings
from src.db import dict_cursor, get_conn

mcp = FastMCP(
    "mcp-ab-test",
    instructions="A/B testing MCP for mmiri28 solutions. Create experiments, assign variants consistently per user, track conversions, calculate results.",
)


def _assign_variant(experiment_name: str, user_id: str, variants: list[str]) -> str:
    """Consistent hash-based variant assignment. Same user always gets same variant."""
    h = hashlib.sha256(f"{experiment_name}:{user_id}".encode()).hexdigest()
    idx = int(h[:8], 16) % len(variants)
    return variants[idx]


@mcp.tool()
def health_check() -> dict:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM experiments WHERE status = 'active'")
                active = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM experiment_assignments")
                assignments = cur.fetchone()[0]
        return {"ok": True, "active_experiments": active, "total_assignments": assignments}
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
def create_experiment(
    name: str, app_slug: str, variants: list[str],
    goal_event: str, description: str = "",
) -> dict[str, Any]:
    """
    Create a new A/B test experiment.

    Args:
        name:        Unique experiment name (e.g. "checkout_button_color").
        app_slug:    App running this experiment.
        variants:    List of variant names (e.g. ["control", "blue", "green"]).
        goal_event:  Event that counts as conversion (e.g. "purchase_completed").
        description: Optional description.
    """
    if len(variants) < 2:
        return {"ok": False, "error": "Experiment needs at least 2 variants."}

    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                exp_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO experiments
                        (id, name, app_slug, variants, goal_event,
                         description, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, 'active', %s)
                """, [exp_id, name, app_slug,
                      psycopg2.extras.Json(variants),
                      goal_event, description, datetime.now(timezone.utc)])
        return {"ok": True, "experiment_id": exp_id, "name": name,
                "variants": variants, "goal_event": goal_event}
    except psycopg2.IntegrityError as exc:
        return {"ok": False, "error": "Experiment with that name already exists."}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def get_variant(experiment_name: str, user_id: str) -> dict[str, Any]:
    """
    Get the variant assigned to a user for an experiment.

    Deterministic: the same user always gets the same variant.
    Auto-creates assignment record on first call.

    Args:
        experiment_name: Name of the experiment.
        user_id:         User identifier (UUID or any stable string).
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    SELECT id, variants, status, goal_event FROM experiments
                    WHERE name = %s
                """, [experiment_name])
                exp = cur.fetchone()
                if not exp:
                    return {"ok": False, "error": f"Experiment '{experiment_name}' not found"}
                if exp["status"] != "active":
                    return {"ok": False, "error": f"Experiment '{experiment_name}' is {exp['status']}"}

                variant = _assign_variant(experiment_name, user_id, exp["variants"])

                # Record assignment (no-op if exists)
                cur.execute("""
                    INSERT INTO experiment_assignments
                        (id, experiment_id, user_id, variant, assigned_at)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (experiment_id, user_id) DO NOTHING
                """, [str(uuid.uuid4()), exp["id"], user_id, variant,
                      datetime.now(timezone.utc)])

        return {"ok": True, "experiment": experiment_name,
                "user_id": user_id, "variant": variant}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def track_conversion(experiment_name: str, user_id: str, value: float = 0) -> dict[str, Any]:
    """
    Record a conversion event for an experiment.

    Args:
        experiment_name: Name of the experiment.
        user_id:         User who converted.
        value:           Optional revenue/numeric value of the conversion.
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    SELECT ea.experiment_id, ea.variant FROM experiment_assignments ea
                    JOIN experiments e ON e.id = ea.experiment_id
                    WHERE e.name = %s AND ea.user_id = %s
                """, [experiment_name, user_id])
                assignment = cur.fetchone()
                if not assignment:
                    return {"ok": False, "error": "User not assigned to this experiment yet."}

                cur.execute("""
                    INSERT INTO experiment_conversions
                        (id, experiment_id, user_id, variant, value, converted_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, [str(uuid.uuid4()), assignment["experiment_id"],
                      user_id, assignment["variant"], value,
                      datetime.now(timezone.utc)])
        return {"ok": True, "experiment": experiment_name,
                "variant": assignment["variant"], "user_id": user_id, "value": value}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def get_results(experiment_name: str) -> dict[str, Any]:
    """
    Get conversion rates and stats per variant.

    Args:
        experiment_name: Name of the experiment.
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("SELECT * FROM experiments WHERE name = %s", [experiment_name])
                exp = cur.fetchone()
                if not exp:
                    return {"ok": False, "error": f"Experiment '{experiment_name}' not found"}

                cur.execute("""
                    SELECT
                        ea.variant,
                        COUNT(DISTINCT ea.user_id) AS assigned_users,
                        COUNT(DISTINCT ec.user_id) AS converted_users,
                        COALESCE(SUM(ec.value), 0) AS total_value
                    FROM experiment_assignments ea
                    LEFT JOIN experiment_conversions ec
                        ON ec.experiment_id = ea.experiment_id AND ec.user_id = ea.user_id
                    WHERE ea.experiment_id = %s
                    GROUP BY ea.variant
                    ORDER BY ea.variant
                """, [exp["id"]])

                results = []
                for row in cur.fetchall():
                    rate = (row["converted_users"] / row["assigned_users"] * 100) if row["assigned_users"] > 0 else 0
                    results.append({
                        "variant": row["variant"],
                        "assigned_users": row["assigned_users"],
                        "converted_users": row["converted_users"],
                        "conversion_rate": round(rate, 2),
                        "total_value": float(row["total_value"]),
                    })

        # Pick winner (highest conversion rate)
        if results:
            winner = max(results, key=lambda r: r["conversion_rate"])
        else:
            winner = None

        return {
            "ok": True, "experiment": experiment_name,
            "status": exp["status"], "goal_event": exp["goal_event"],
            "results": results,
            "leading_variant": winner["variant"] if winner else None,
            "note": "Statistical significance requires manual analysis. These are raw rates.",
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def list_experiments(app_slug: str | None = None) -> dict[str, Any]:
    """List all experiments, optionally filtered by app."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                if app_slug:
                    cur.execute("SELECT * FROM experiments WHERE app_slug = %s ORDER BY created_at DESC", [app_slug])
                else:
                    cur.execute("SELECT * FROM experiments ORDER BY created_at DESC")
                exps = [dict(r) for r in cur.fetchall()]
        return {"ok": True, "count": len(exps), "experiments": exps}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def end_experiment(experiment_name: str, winning_variant: str | None = None) -> dict[str, Any]:
    """
    End an experiment, optionally recording the winning variant.
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    UPDATE experiments
                    SET status = 'ended', ended_at = NOW(), winning_variant = %s
                    WHERE name = %s RETURNING id
                """, [winning_variant, experiment_name])
                if not cur.fetchone():
                    return {"ok": False, "error": "Experiment not found"}
        return {"ok": True, "experiment": experiment_name, "winning_variant": winning_variant}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
