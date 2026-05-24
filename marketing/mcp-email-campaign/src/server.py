"""server.py — mcp-email-campaign MCP server entry point.

Email list management and broadcast campaigns via Resend.
Subscribers, unsubscribes, campaigns, basic stats.
"""

import secrets
import subprocess
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
import psycopg2

from mcp.server.fastmcp import FastMCP
from src.config import settings
from src.db import dict_cursor, get_conn

mcp = FastMCP(
    "mcp-email-campaign",
    instructions="Email campaign MCP for mmiri28 solutions. Manage subscriber lists, send broadcasts via Resend, track basic stats.",
)


@mcp.tool()
def health_check() -> dict:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM email_lists")
                lists = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM email_subscribers")
                subs = cur.fetchone()[0]
        return {"ok": True, "lists": lists, "total_subscribers": subs,
                "resend_configured": bool(settings.resend_api_key and "your-" not in settings.resend_api_key)}
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
def create_list(name: str, app_slug: str, description: str = "") -> dict[str, Any]:
    """Create a new subscriber list."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                list_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO email_lists (id, name, app_slug, description, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, [list_id, name, app_slug, description, datetime.now(timezone.utc)])
        return {"ok": True, "list_id": list_id, "name": name, "app_slug": app_slug}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def add_subscriber(
    list_id: str, email: str, name: str = "",
    metadata: dict | None = None,
) -> dict[str, Any]:
    """
    Add a subscriber to a list.

    Args:
        list_id:  UUID of the list.
        email:    Subscriber email.
        name:     Subscriber name (optional).
        metadata: Extra data (source, tags, etc.)
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                sub_id = str(uuid.uuid4())
                unsubscribe_token = secrets.token_urlsafe(32)
                cur.execute("""
                    INSERT INTO email_subscribers
                        (id, list_id, email, name, metadata,
                         unsubscribe_token, is_active, subscribed_at)
                    VALUES (%s, %s, %s, %s, %s, %s, true, %s)
                    ON CONFLICT (list_id, email) DO UPDATE SET
                        is_active = true, name = EXCLUDED.name
                    RETURNING id, unsubscribe_token
                """, [sub_id, list_id, email.lower().strip(), name,
                      psycopg2.extras.Json(metadata or {}),
                      unsubscribe_token, datetime.now(timezone.utc)])
                row = cur.fetchone()
        return {"ok": True, "subscriber_id": row["id"], "email": email.lower().strip(),
                "unsubscribe_url": f"{settings.unsubscribe_base_url}?token={row['unsubscribe_token']}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def remove_subscriber(token: str | None = None, email: str | None = None,
                      list_id: str | None = None) -> dict[str, Any]:
    """
    Unsubscribe a subscriber. Use token (from unsubscribe link) or email+list_id.
    """
    if not token and not (email and list_id):
        return {"ok": False, "error": "Provide either token, or email + list_id."}
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                if token:
                    cur.execute("""
                        UPDATE email_subscribers SET is_active = false, unsubscribed_at = NOW()
                        WHERE unsubscribe_token = %s AND is_active = true RETURNING email
                    """, [token])
                else:
                    cur.execute("""
                        UPDATE email_subscribers SET is_active = false, unsubscribed_at = NOW()
                        WHERE email = %s AND list_id = %s AND is_active = true RETURNING email
                    """, [email.lower().strip(), list_id])
                row = cur.fetchone()
        if not row:
            return {"ok": False, "error": "Subscriber not found or already unsubscribed."}
        return {"ok": True, "email": row["email"], "unsubscribed": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def list_subscribers(list_id: str, limit: int = 100,
                     active_only: bool = True) -> dict[str, Any]:
    """List subscribers in a list."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                where = "list_id = %s"
                params: list = [list_id]
                if active_only:
                    where += " AND is_active = true"
                cur.execute(f"""
                    SELECT id, email, name, is_active, subscribed_at, unsubscribed_at, metadata
                    FROM email_subscribers WHERE {where}
                    ORDER BY subscribed_at DESC LIMIT %s
                """, params + [min(limit, 1000)])
                subs = [dict(r) for r in cur.fetchall()]
        return {"ok": True, "list_id": list_id, "count": len(subs), "subscribers": subs}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def send_campaign(
    list_id: str, subject: str, html: str,
    from_address: str | None = None, test_mode: bool = False,
) -> dict[str, Any]:
    """
    Send an email broadcast to all active subscribers in a list.

    Args:
        list_id:      UUID of the list.
        subject:      Email subject.
        html:         HTML body. Use {{unsubscribe_url}} as a placeholder.
        from_address: Sender. Default: EMAIL_FROM.
        test_mode:    If True, sends only to the first 3 subscribers.
    """
    if not settings.resend_api_key or "your-" in settings.resend_api_key:
        return {"ok": False, "error": "RESEND_API_KEY not configured."}

    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                limit = 3 if test_mode else 10000
                cur.execute("""
                    SELECT email, name, unsubscribe_token FROM email_subscribers
                    WHERE list_id = %s AND is_active = true LIMIT %s
                """, [list_id, limit])
                subscribers = cur.fetchall()

                if not subscribers:
                    return {"ok": False, "error": "No active subscribers in list."}

                # Create campaign record
                campaign_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO email_campaigns
                        (id, list_id, subject, html_body, status,
                         recipient_count, test_mode, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, [campaign_id, list_id, subject, html, "sending",
                      len(subscribers), test_mode, datetime.now(timezone.utc)])

        sent = 0
        failed = 0
        for sub in subscribers:
            unsubscribe_url = f"{settings.unsubscribe_base_url}?token={sub['unsubscribe_token']}"
            personalized_html = html.replace("{{unsubscribe_url}}", unsubscribe_url) \
                                   .replace("{{name}}", sub.get("name") or "")
            try:
                r = httpx.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {settings.resend_api_key}",
                             "Content-Type": "application/json"},
                    json={
                        "from": from_address or settings.email_from,
                        "to": [sub["email"]],
                        "subject": subject,
                        "html": personalized_html,
                        "headers": {"List-Unsubscribe": f"<{unsubscribe_url}>"},
                    },
                    timeout=10,
                )
                if r.status_code in (200, 201):
                    sent += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

        # Update campaign
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    UPDATE email_campaigns
                    SET status = 'sent', sent_count = %s, failed_count = %s, sent_at = NOW()
                    WHERE id = %s
                """, [sent, failed, campaign_id])

        return {
            "ok": True, "campaign_id": campaign_id,
            "recipients": len(subscribers),
            "sent": sent, "failed": failed,
            "test_mode": test_mode,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def get_campaign_stats(campaign_id: str) -> dict[str, Any]:
    """Get sending stats for a campaign."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("SELECT * FROM email_campaigns WHERE id = %s", [campaign_id])
                campaign = cur.fetchone()
        if not campaign:
            return {"ok": False, "error": "Campaign not found"}
        return {"ok": True, "campaign": dict(campaign)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
