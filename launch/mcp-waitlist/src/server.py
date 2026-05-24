"""server.py — mcp-waitlist MCP server entry point.

Waitlist management with referral codes.
Each signup gets a unique code. Referrals move people up the list.
"""

import secrets
import subprocess
import uuid
from datetime import datetime, timezone
from typing import Any

import psycopg2

from mcp.server.fastmcp import FastMCP
from src.config import settings
from src.db import dict_cursor, get_conn

mcp = FastMCP(
    "mcp-waitlist",
    instructions="Waitlist MCP for mmiri28 solutions. Pre-launch signups with referral codes. Referrals boost users up the list. Invite top N when ready.",
)


def _new_referral_code() -> str:
    return secrets.token_urlsafe(6).replace("_", "").replace("-", "")[:10]


@mcp.tool()
def health_check() -> dict:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM waitlists")
                lists = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM waitlist_entries WHERE status = 'waiting'")
                waiting = cur.fetchone()[0]
        return {"ok": True, "waitlists": lists, "total_waiting": waiting}
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
def create_waitlist(name: str, app_slug: str, description: str = "") -> dict[str, Any]:
    """
    Create a new waitlist for a product launch.

    Args:
        name:        Waitlist name (e.g. "Marketplace Early Access").
        app_slug:    App this waitlist belongs to.
        description: Short description shown to signups.
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                waitlist_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO waitlists (id, name, app_slug, description, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, [waitlist_id, name, app_slug, description, datetime.now(timezone.utc)])
        return {"ok": True, "waitlist_id": waitlist_id, "name": name, "app_slug": app_slug}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def join_waitlist(
    waitlist_id: str, email: str, name: str = "",
    referred_by_code: str | None = None, metadata: dict | None = None,
) -> dict[str, Any]:
    """
    Add an email to a waitlist.

    A new referral code is generated for this signup.
    If referred_by_code is valid, the referrer moves up 5 positions.

    Args:
        waitlist_id:      The waitlist to join.
        email:            Subscriber email.
        name:             Optional name.
        referred_by_code: Referral code of who referred them.
        metadata:         Custom data (source, tags, etc.)
    """
    try:
        email = email.lower().strip()
        referral_code = _new_referral_code()

        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                # Check if already on the list
                cur.execute("""
                    SELECT id, position, referral_code FROM waitlist_entries
                    WHERE waitlist_id = %s AND email = %s
                """, [waitlist_id, email])
                existing = cur.fetchone()
                if existing:
                    return {"ok": True, "already_joined": True,
                            "email": email, "position": existing["position"],
                            "referral_code": existing["referral_code"]}

                # Get the next position (end of list)
                cur.execute("""
                    SELECT COALESCE(MAX(position), 0) + 1 AS next_pos
                    FROM waitlist_entries WHERE waitlist_id = %s
                """, [waitlist_id])
                position = cur.fetchone()["next_pos"]

                # Look up referrer
                referred_by_id = None
                if referred_by_code:
                    cur.execute("""
                        SELECT id FROM waitlist_entries
                        WHERE waitlist_id = %s AND referral_code = %s
                    """, [waitlist_id, referred_by_code])
                    ref = cur.fetchone()
                    if ref:
                        referred_by_id = ref["id"]

                entry_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO waitlist_entries
                        (id, waitlist_id, email, name, position, referral_code,
                         referred_by_id, metadata, status, joined_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'waiting', %s)
                """, [entry_id, waitlist_id, email, name, position, referral_code,
                      referred_by_id, psycopg2.extras.Json(metadata or {}),
                      datetime.now(timezone.utc)])

                # Boost referrer if applicable
                if referred_by_id:
                    cur.execute("""
                        UPDATE waitlist_entries SET position = GREATEST(1, position - 5)
                        WHERE id = %s
                    """, [referred_by_id])

        return {
            "ok": True, "entry_id": entry_id, "email": email,
            "position": position, "referral_code": referral_code,
            "referred_by_id": referred_by_id,
            "share_message": f"You're on the waitlist! Share your code '{referral_code}' to move up 5 spots for each referral.",
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def get_position(email: str | None = None,
                 referral_code: str | None = None,
                 waitlist_id: str | None = None) -> dict[str, Any]:
    """
    Look up a signup by email or referral code.

    Args:
        email:         Email to look up.
        referral_code: Referral code to look up.
        waitlist_id:   Required if looking up by email (codes are globally unique).
    """
    if not email and not referral_code:
        return {"ok": False, "error": "Provide email or referral_code."}

    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                if email:
                    if not waitlist_id:
                        return {"ok": False, "error": "waitlist_id required when looking up by email."}
                    cur.execute("""
                        SELECT * FROM waitlist_entries
                        WHERE waitlist_id = %s AND email = %s
                    """, [waitlist_id, email.lower().strip()])
                else:
                    cur.execute("SELECT * FROM waitlist_entries WHERE referral_code = %s",
                                [referral_code])
                entry = cur.fetchone()
                if not entry:
                    return {"ok": False, "error": "Not found on waitlist."}

                cur.execute("""
                    SELECT COUNT(*) AS total FROM waitlist_entries
                    WHERE waitlist_id = %s AND status = 'waiting'
                """, [entry["waitlist_id"]])
                total = cur.fetchone()["total"]

                cur.execute("""
                    SELECT COUNT(*) AS referred FROM waitlist_entries
                    WHERE referred_by_id = %s
                """, [entry["id"]])
                referred = cur.fetchone()["referred"]

        return {
            "ok": True, "email": entry["email"], "name": entry["name"],
            "position": entry["position"], "total_on_list": total,
            "status": entry["status"],
            "referral_code": entry["referral_code"],
            "referrals_made": referred,
            "joined_at": entry["joined_at"],
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def list_top(waitlist_id: str, limit: int = 25) -> dict[str, Any]:
    """List the top N waiting signups for a waitlist."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    SELECT email, name, position, referral_code, joined_at
                    FROM waitlist_entries
                    WHERE waitlist_id = %s AND status = 'waiting'
                    ORDER BY position ASC, joined_at ASC LIMIT %s
                """, [waitlist_id, min(limit, 200)])
                entries = [dict(r) for r in cur.fetchall()]
        return {"ok": True, "count": len(entries), "top_entries": entries}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def invite_top(waitlist_id: str, count: int = 50) -> dict[str, Any]:
    """
    Mark the top N waiting signups as 'invited'.

    Use this when you're ready to send out access invitations.
    Combine with mcp-notifications to email them.

    Args:
        waitlist_id: The waitlist.
        count:       How many to invite.
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    WITH top_entries AS (
                        SELECT id FROM waitlist_entries
                        WHERE waitlist_id = %s AND status = 'waiting'
                        ORDER BY position ASC LIMIT %s
                    )
                    UPDATE waitlist_entries
                    SET status = 'invited', invited_at = NOW()
                    WHERE id IN (SELECT id FROM top_entries)
                    RETURNING email, name
                """, [waitlist_id, min(count, 500)])
                invited = [dict(r) for r in cur.fetchall()]
        return {"ok": True, "invited_count": len(invited), "invited": invited,
                "next_step": "Use mcp-notifications send_bulk_email to send invitations."}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def get_waitlist_stats(waitlist_id: str) -> dict[str, Any]:
    """Get waitlist stats — total signups, status breakdown, top referrers."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    SELECT status, COUNT(*) AS count
                    FROM waitlist_entries WHERE waitlist_id = %s GROUP BY status
                """, [waitlist_id])
                by_status = {r["status"]: r["count"] for r in cur.fetchall()}

                cur.execute("""
                    SELECT e.email, e.referral_code, COUNT(r.id) AS referrals
                    FROM waitlist_entries e
                    LEFT JOIN waitlist_entries r ON r.referred_by_id = e.id
                    WHERE e.waitlist_id = %s
                    GROUP BY e.id, e.email, e.referral_code
                    HAVING COUNT(r.id) > 0
                    ORDER BY COUNT(r.id) DESC LIMIT 10
                """, [waitlist_id])
                top_referrers = [dict(r) for r in cur.fetchall()]

        return {"ok": True, "by_status": by_status, "top_referrers": top_referrers,
                "total": sum(by_status.values())}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def list_waitlists(app_slug: str | None = None) -> dict[str, Any]:
    """List all waitlists."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                if app_slug:
                    cur.execute("""
                        SELECT w.*, COUNT(e.id) AS total_signups
                        FROM waitlists w
                        LEFT JOIN waitlist_entries e ON e.waitlist_id = w.id
                        WHERE w.app_slug = %s
                        GROUP BY w.id ORDER BY w.created_at DESC
                    """, [app_slug])
                else:
                    cur.execute("""
                        SELECT w.*, COUNT(e.id) AS total_signups
                        FROM waitlists w
                        LEFT JOIN waitlist_entries e ON e.waitlist_id = w.id
                        GROUP BY w.id ORDER BY w.created_at DESC
                    """)
                waitlists = [dict(r) for r in cur.fetchall()]
        return {"ok": True, "count": len(waitlists), "waitlists": waitlists}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
