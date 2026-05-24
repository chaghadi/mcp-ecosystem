"""server.py — mcp-code-review MCP server entry point.

PR review tracking and assignments.
Decouples GitHub PRs from review workflow — assign reviewers,
track decisions, surface stale reviews.
"""

import subprocess
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import psycopg2

from mcp.server.fastmcp import FastMCP
from src.config import settings
from src.db import dict_cursor, get_conn

mcp = FastMCP(
    "mcp-code-review",
    instructions="Code review MCP for mmiri28 solutions. Track PR review requests, assign reviewers, log decisions, calculate review stats, nudge stale reviews.",
)


@mcp.tool()
def health_check() -> dict:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM review_requests WHERE status = 'open'")
                open_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM review_assignments WHERE status = 'pending'")
                pending = cur.fetchone()[0]
        return {"ok": True, "open_requests": open_count, "pending_reviews": pending}
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
def register_pr(
    repo: str, pr_number: int, pr_title: str,
    pr_url: str, app_slug: str, requested_by: str,
) -> dict[str, Any]:
    """
    Register a PR that needs review.

    Args:
        repo:          Repo name (e.g. "chaghadi/mcp-ecosystem").
        pr_number:     PR number.
        pr_title:      PR title.
        pr_url:        Full URL to the PR.
        app_slug:      App context.
        requested_by:  Author or person requesting reviews.
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                request_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO review_requests
                        (id, repo, pr_number, pr_title, pr_url, app_slug,
                         requested_by, status, requested_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'open', %s)
                    ON CONFLICT (repo, pr_number) DO UPDATE SET
                        pr_title = EXCLUDED.pr_title,
                        status = 'open'
                    RETURNING id
                """, [request_id, repo, pr_number, pr_title, pr_url,
                      app_slug, requested_by, datetime.now(timezone.utc)])
                final_id = cur.fetchone()["id"]
        return {"ok": True, "request_id": final_id, "repo": repo, "pr_number": pr_number}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def assign_reviewer(request_id: str, reviewer: str) -> dict[str, Any]:
    """
    Assign a reviewer to a PR.

    Args:
        request_id: review request UUID from register_pr.
        reviewer:   Reviewer username or email.
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                assignment_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO review_assignments
                        (id, review_request_id, reviewer, status, assigned_at)
                    VALUES (%s, %s, %s, 'pending', %s)
                    ON CONFLICT (review_request_id, reviewer) DO NOTHING
                    RETURNING id
                """, [assignment_id, request_id, reviewer, datetime.now(timezone.utc)])
                row = cur.fetchone()
                if not row:
                    return {"ok": True, "already_assigned": True,
                            "request_id": request_id, "reviewer": reviewer}
        return {"ok": True, "assignment_id": row["id"], "reviewer": reviewer}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def complete_review(
    assignment_id: str, decision: str, comments: str = "",
) -> dict[str, Any]:
    """
    Record a completed review.

    Args:
        assignment_id: Assignment UUID.
        decision:      "approved" | "changes_requested" | "commented"
        comments:      Review notes.
    """
    if decision not in {"approved", "changes_requested", "commented"}:
        return {"ok": False, "error": "decision must be approved/changes_requested/commented"}
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    UPDATE review_assignments
                    SET status = 'completed', decision = %s, comments = %s, completed_at = NOW()
                    WHERE id = %s RETURNING review_request_id, reviewer
                """, [decision, comments, assignment_id])
                row = cur.fetchone()
                if not row:
                    return {"ok": False, "error": "Assignment not found"}

                # If decision is approved and all assignments approved, close the request
                if decision == "approved":
                    cur.execute("""
                        SELECT COUNT(*) AS total,
                               SUM(CASE WHEN status = 'completed' AND decision = 'approved' THEN 1 ELSE 0 END) AS approved
                        FROM review_assignments WHERE review_request_id = %s
                    """, [row["review_request_id"]])
                    stats = cur.fetchone()
                    if stats["approved"] == stats["total"]:
                        cur.execute("""
                            UPDATE review_requests SET status = 'approved', closed_at = NOW()
                            WHERE id = %s
                        """, [row["review_request_id"]])

        return {"ok": True, "assignment_id": assignment_id,
                "decision": decision, "reviewer": row["reviewer"]}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def list_pending_reviews(reviewer: str) -> dict[str, Any]:
    """List pending review assignments for a specific reviewer."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    SELECT a.id, a.assigned_at, r.repo, r.pr_number, r.pr_title,
                           r.pr_url, r.requested_by, r.app_slug
                    FROM review_assignments a
                    JOIN review_requests r ON r.id = a.review_request_id
                    WHERE a.reviewer = %s AND a.status = 'pending'
                      AND r.status = 'open'
                    ORDER BY a.assigned_at ASC
                """, [reviewer])
                pending = [dict(r) for r in cur.fetchall()]
        return {"ok": True, "reviewer": reviewer, "count": len(pending),
                "pending_reviews": pending}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def get_review_stats(reviewer: str, days_back: int = 30) -> dict[str, Any]:
    """
    Get review stats for a reviewer over the past N days.
    """
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    SELECT
                        COUNT(*) AS total,
                        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed,
                        SUM(CASE WHEN decision = 'approved' THEN 1 ELSE 0 END) AS approved,
                        SUM(CASE WHEN decision = 'changes_requested' THEN 1 ELSE 0 END) AS changes_requested,
                        AVG(EXTRACT(EPOCH FROM (completed_at - assigned_at))/3600)
                            FILTER (WHERE completed_at IS NOT NULL) AS avg_hours_to_review
                    FROM review_assignments
                    WHERE reviewer = %s AND assigned_at >= %s
                """, [reviewer, cutoff])
                stats = dict(cur.fetchone())
        return {
            "ok": True, "reviewer": reviewer, "period_days": days_back,
            "total_assigned": stats["total"] or 0,
            "completed": stats["completed"] or 0,
            "approved": stats["approved"] or 0,
            "changes_requested": stats["changes_requested"] or 0,
            "avg_hours_to_review": round(stats["avg_hours_to_review"] or 0, 1),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def nudge_pending(hours_threshold: int = 24) -> dict[str, Any]:
    """
    Find stale review assignments — pending more than N hours.
    Useful for sending follow-up reminders.

    Args:
        hours_threshold: Reviews older than this need a nudge.
    """
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_threshold)
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    SELECT a.id, a.reviewer, a.assigned_at,
                           r.repo, r.pr_number, r.pr_title, r.pr_url, r.requested_by
                    FROM review_assignments a
                    JOIN review_requests r ON r.id = a.review_request_id
                    WHERE a.status = 'pending'
                      AND r.status = 'open'
                      AND a.assigned_at < %s
                    ORDER BY a.assigned_at ASC
                """, [cutoff])
                stale = [dict(r) for r in cur.fetchall()]
        return {"ok": True, "threshold_hours": hours_threshold,
                "stale_count": len(stale), "stale_reviews": stale,
                "next_step": "Use mcp-slack-ops or mcp-notifications to send reminders."}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
