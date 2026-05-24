"""server.py — mcp-press MCP server entry point.

Press release management, media contacts, outreach log.
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
    "mcp-press",
    instructions="Press and PR management MCP for mmiri28 solutions. Store press releases, manage media contacts, track outreach.",
)


@mcp.tool()
def health_check() -> dict:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM press_releases")
                releases = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM media_contacts")
                contacts = cur.fetchone()[0]
        return {"ok": True, "press_releases": releases, "media_contacts": contacts}
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
def create_press_release(
    title: str, content: str, app_slug: str,
    embargo_date: str | None = None, contact_info: str = "",
) -> dict[str, Any]:
    """
    Store a press release.

    Args:
        title:        Headline.
        content:      Full press release body (markdown or HTML).
        app_slug:     App this release is about.
        embargo_date: ISO datetime when this can be published. None = immediate.
        contact_info: Press contact details (name, email, phone).
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                pr_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO press_releases
                        (id, title, content, app_slug, embargo_date,
                         contact_info, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, 'draft', %s)
                """, [pr_id, title, content, app_slug, embargo_date,
                      contact_info, datetime.now(timezone.utc)])
        return {"ok": True, "press_release_id": pr_id, "title": title,
                "embargo_date": embargo_date}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def get_press_release(press_release_id: str) -> dict[str, Any]:
    """Get a press release by ID."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("SELECT * FROM press_releases WHERE id = %s", [press_release_id])
                pr = cur.fetchone()
        if not pr:
            return {"ok": False, "error": "Press release not found"}
        return {"ok": True, "press_release": dict(pr)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def list_press_releases(app_slug: str | None = None,
                        status: str | None = None) -> dict[str, Any]:
    """List press releases."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                conditions = []
                params: list = []
                if app_slug:
                    conditions.append("app_slug = %s")
                    params.append(app_slug)
                if status:
                    conditions.append("status = %s")
                    params.append(status)
                where = "WHERE " + " AND ".join(conditions) if conditions else ""
                cur.execute(f"SELECT id, title, app_slug, status, embargo_date, created_at FROM press_releases {where} ORDER BY created_at DESC", params)
                releases = [dict(r) for r in cur.fetchall()]
        return {"ok": True, "count": len(releases), "press_releases": releases}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def add_media_contact(
    name: str, email: str, outlet: str,
    beat: str = "", twitter: str = "", notes: str = "",
) -> dict[str, Any]:
    """
    Add a media contact.

    Args:
        name:    Journalist name.
        email:   Their email.
        outlet:  Publication (e.g. "TechCrunch", "Wired").
        beat:    What they cover (e.g. "ai", "fintech", "africa-tech").
        twitter: Their Twitter handle.
        notes:   Notes about relationship history.
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                contact_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO media_contacts
                        (id, name, email, outlet, beat, twitter, notes, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, [contact_id, name, email.lower().strip(), outlet,
                      beat, twitter, notes, datetime.now(timezone.utc)])
        return {"ok": True, "contact_id": contact_id, "name": name, "outlet": outlet}
    except psycopg2.IntegrityError:
        return {"ok": False, "error": "Contact with that email already exists."}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def list_media_contacts(beat: str | None = None, outlet: str | None = None) -> dict[str, Any]:
    """List media contacts, optionally filtered by beat or outlet."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                conditions = []
                params: list = []
                if beat:
                    conditions.append("beat = %s")
                    params.append(beat)
                if outlet:
                    conditions.append("outlet = %s")
                    params.append(outlet)
                where = "WHERE " + " AND ".join(conditions) if conditions else ""
                cur.execute(f"SELECT * FROM media_contacts {where} ORDER BY outlet, name", params)
                contacts = [dict(r) for r in cur.fetchall()]
        return {"ok": True, "count": len(contacts), "contacts": contacts}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def log_outreach(
    contact_id: str, press_release_id: str,
    status: str = "sent", notes: str = "",
) -> dict[str, Any]:
    """
    Log an outreach attempt to a media contact.

    Args:
        contact_id:       Media contact UUID.
        press_release_id: Which press release was sent.
        status:           "sent", "opened", "replied", "covered", "declined".
        notes:            Free-form notes.
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                outreach_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO outreach_log
                        (id, contact_id, press_release_id, status, notes, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, [outreach_id, contact_id, press_release_id,
                      status, notes, datetime.now(timezone.utc)])
        return {"ok": True, "outreach_id": outreach_id, "status": status}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def get_outreach_log(press_release_id: str | None = None,
                     contact_id: str | None = None) -> dict[str, Any]:
    """View outreach history."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                conditions = []
                params: list = []
                if press_release_id:
                    conditions.append("o.press_release_id = %s")
                    params.append(press_release_id)
                if contact_id:
                    conditions.append("o.contact_id = %s")
                    params.append(contact_id)
                where = "WHERE " + " AND ".join(conditions) if conditions else ""
                cur.execute(f"""
                    SELECT o.*, c.name AS contact_name, c.outlet, p.title AS press_release_title
                    FROM outreach_log o
                    LEFT JOIN media_contacts c ON c.id = o.contact_id
                    LEFT JOIN press_releases p ON p.id = o.press_release_id
                    {where} ORDER BY o.created_at DESC
                """, params)
                log = [dict(r) for r in cur.fetchall()]
        return {"ok": True, "count": len(log), "outreach_log": log}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
