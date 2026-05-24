"""server.py — mcp-social-listen MCP server entry point.

Track brand mentions and keywords across social platforms.
Currently supports Twitter/X search API.
"""

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
    "mcp-social-listen",
    instructions="Social listening MCP for mmiri28 solutions. Track brand mentions and keywords on Twitter/X. Stores results in Postgres for trend analysis.",
)


@mcp.tool()
def health_check() -> dict:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM tracked_keywords")
                keywords = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM mentions")
                mentions = cur.fetchone()[0]
        return {"ok": True, "tracked_keywords": keywords, "total_mentions": mentions,
                "twitter_configured": bool(settings.twitter_bearer and "your-" not in settings.twitter_bearer)}
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
def track_keyword(keyword: str, app_slug: str, platforms: list[str] | None = None) -> dict[str, Any]:
    """
    Register a keyword to track mentions of.

    Args:
        keyword:   Keyword, hashtag, or brand name to monitor.
        app_slug:  Which app this keyword belongs to.
        platforms: List of platforms to monitor (currently only "twitter" supported).
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                keyword_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO tracked_keywords
                        (id, keyword, app_slug, platforms, is_active, created_at)
                    VALUES (%s, %s, %s, %s, true, %s)
                """, [keyword_id, keyword, app_slug,
                      psycopg2.extras.Json(platforms or ["twitter"]),
                      datetime.now(timezone.utc)])
        return {"ok": True, "keyword_id": keyword_id, "keyword": keyword,
                "platforms": platforms or ["twitter"]}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def fetch_twitter_mentions(keyword: str, max_results: int = 50) -> dict[str, Any]:
    """
    Fetch recent Twitter/X mentions of a keyword.

    Args:
        keyword:     Keyword or hashtag to search for.
        max_results: Max tweets to fetch (10-100).
    """
    if not settings.twitter_bearer or "your-" in settings.twitter_bearer:
        return {"ok": False, "error": "TWITTER_BEARER_TOKEN not configured."}

    try:
        r = httpx.get(
            "https://api.twitter.com/2/tweets/search/recent",
            headers={"Authorization": f"Bearer {settings.twitter_bearer}"},
            params={
                "query": keyword, "max_results": min(max(10, max_results), 100),
                "tweet.fields": "created_at,author_id,public_metrics,lang",
            },
            timeout=15,
        )
        if r.status_code != 200:
            return {"ok": False, "error": f"Twitter API: HTTP {r.status_code}: {r.text[:200]}"}

        data = r.json()
        tweets = data.get("data", [])

        # Store mentions
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                for tweet in tweets:
                    cur.execute("""
                        INSERT INTO mentions
                            (id, platform, platform_id, keyword, content,
                             author_id, metrics, language, created_at, fetched_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (platform, platform_id) DO NOTHING
                    """, [str(uuid.uuid4()), "twitter", tweet["id"], keyword,
                          tweet["text"], tweet.get("author_id"),
                          psycopg2.extras.Json(tweet.get("public_metrics", {})),
                          tweet.get("lang"), tweet.get("created_at"),
                          datetime.now(timezone.utc)])

        return {"ok": True, "keyword": keyword,
                "fetched": len(tweets),
                "tweets": [{"id": t["id"], "text": t["text"][:200],
                            "metrics": t.get("public_metrics", {})}
                           for t in tweets[:10]]}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def get_mentions(
    keyword: str | None = None, app_slug: str | None = None,
    since_hours: int = 24, limit: int = 50,
) -> dict[str, Any]:
    """
    Query stored mentions.

    Args:
        keyword:     Filter by keyword.
        app_slug:    Filter by app (joins with tracked_keywords).
        since_hours: Only mentions from the last N hours.
        limit:       Max results.
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                conditions = ["m.created_at > NOW() - INTERVAL '%s hours'"]
                params: list = [since_hours]
                if keyword:
                    conditions.append("m.keyword = %s")
                    params.append(keyword)
                if app_slug:
                    conditions.append("tk.app_slug = %s")
                    params.append(app_slug)

                where = " AND ".join(conditions)
                cur.execute(f"""
                    SELECT DISTINCT m.* FROM mentions m
                    LEFT JOIN tracked_keywords tk ON tk.keyword = m.keyword
                    WHERE {where}
                    ORDER BY m.created_at DESC LIMIT %s
                """, params + [min(limit, 200)])
                mentions = [dict(r) for r in cur.fetchall()]
        return {"ok": True, "count": len(mentions), "mentions": mentions}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def list_keywords(app_slug: str | None = None) -> dict[str, Any]:
    """List all tracked keywords, optionally filtered by app."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                if app_slug:
                    cur.execute("SELECT * FROM tracked_keywords WHERE app_slug = %s ORDER BY created_at DESC", [app_slug])
                else:
                    cur.execute("SELECT * FROM tracked_keywords ORDER BY created_at DESC")
                keywords = [dict(r) for r in cur.fetchall()]
        return {"ok": True, "count": len(keywords), "keywords": keywords}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def delete_keyword(keyword_id: str) -> dict[str, Any]:
    """Stop tracking a keyword."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("DELETE FROM tracked_keywords WHERE id = %s", [keyword_id])
                removed = cur.rowcount > 0
        return {"ok": True, "removed": removed, "keyword_id": keyword_id}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
