"""server.py — mcp-docs MCP server entry point.

Internal documentation system. Markdown content stored in Postgres,
searchable by title/content/tags, organised by category and app.
"""

import re
import subprocess
import uuid
from datetime import datetime, timezone
from typing import Any

import psycopg2

from mcp.server.fastmcp import FastMCP
from src.config import settings
from src.db import dict_cursor, get_conn

mcp = FastMCP(
    "mcp-docs",
    instructions="Internal docs MCP for mmiri28 solutions. Markdown documentation stored in Postgres. Search by title, content, or tags.",
)


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text[:100]


@mcp.tool()
def health_check() -> dict:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM docs")
                total = cur.fetchone()[0]
        return {"ok": True, "total_docs": total}
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
def create_doc(
    title: str, content: str, app_slug: str,
    category: str = "general", tags: list[str] | None = None,
    author: str = "",
) -> dict[str, Any]:
    """
    Create a documentation page.

    Args:
        title:    Doc title.
        content:  Markdown content.
        app_slug: App this doc belongs to.
        category: Category (e.g. "engineering", "ops", "design", "general").
        tags:     List of tags for filtering.
        author:   Who wrote it (username or email).
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                doc_id = str(uuid.uuid4())
                slug = _slugify(title)
                # Ensure unique slug per app
                base_slug = slug
                counter = 1
                while True:
                    cur.execute("SELECT id FROM docs WHERE slug = %s AND app_slug = %s",
                                [slug, app_slug])
                    if not cur.fetchone():
                        break
                    counter += 1
                    slug = f"{base_slug}-{counter}"

                cur.execute("""
                    INSERT INTO docs (id, title, slug, content, app_slug, category,
                                       tags, author, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [doc_id, title, slug, content, app_slug, category,
                      psycopg2.extras.Json(tags or []), author,
                      datetime.now(timezone.utc), datetime.now(timezone.utc)])
        return {"ok": True, "doc_id": doc_id, "slug": slug, "title": title}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def get_doc(slug_or_id: str, app_slug: str | None = None) -> dict[str, Any]:
    """
    Get a doc by slug or UUID.

    Args:
        slug_or_id: Slug (e.g. "deployment-guide") or UUID.
        app_slug:   Required if looking up by slug (slugs are per-app).
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                # Try as UUID first
                try:
                    uuid.UUID(slug_or_id)
                    cur.execute("SELECT * FROM docs WHERE id = %s", [slug_or_id])
                except ValueError:
                    if not app_slug:
                        return {"ok": False, "error": "app_slug required when looking up by slug."}
                    cur.execute("SELECT * FROM docs WHERE slug = %s AND app_slug = %s",
                                [slug_or_id, app_slug])
                doc = cur.fetchone()
        if not doc:
            return {"ok": False, "error": "Doc not found"}
        return {"ok": True, "doc": dict(doc)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def update_doc(
    doc_id: str, content: str | None = None,
    title: str | None = None, category: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Update a doc. Only provided fields are changed."""
    if content is None and title is None and category is None and tags is None:
        return {"ok": False, "error": "Provide at least one field to update."}
    updates: list = []
    params: list = []
    if content is not None:
        updates.append("content = %s"); params.append(content)
    if title is not None:
        updates.append("title = %s"); params.append(title)
    if category is not None:
        updates.append("category = %s"); params.append(category)
    if tags is not None:
        updates.append("tags = %s"); params.append(psycopg2.extras.Json(tags))
    updates.append("updated_at = %s"); params.append(datetime.now(timezone.utc))
    params.append(doc_id)

    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute(f"UPDATE docs SET {', '.join(updates)} WHERE id = %s RETURNING id",
                            params)
                if not cur.fetchone():
                    return {"ok": False, "error": "Doc not found"}
        return {"ok": True, "doc_id": doc_id, "updated_fields": len(updates) - 1}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def delete_doc(doc_id: str) -> dict[str, Any]:
    """Delete a doc."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("DELETE FROM docs WHERE id = %s", [doc_id])
                deleted = cur.rowcount > 0
        return {"ok": True, "deleted": deleted, "doc_id": doc_id}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def search_docs(
    query: str, app_slug: str | None = None,
    category: str | None = None, limit: int = 20,
) -> dict[str, Any]:
    """
    Search docs by title, content, or tags.

    Args:
        query:    Search term (min 2 chars).
        app_slug: Filter to one app.
        category: Filter to one category.
        limit:    Max results.
    """
    if len(query.strip()) < 2:
        return {"ok": False, "error": "query must be at least 2 characters."}
    try:
        conditions = ["(title ILIKE %s OR content ILIKE %s OR tags::text ILIKE %s)"]
        pattern = f"%{query}%"
        params: list = [pattern, pattern, pattern]
        if app_slug:
            conditions.append("app_slug = %s"); params.append(app_slug)
        if category:
            conditions.append("category = %s"); params.append(category)
        where = " AND ".join(conditions)
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute(f"""
                    SELECT id, title, slug, category, tags, app_slug, updated_at,
                           SUBSTRING(content, 1, 200) AS excerpt
                    FROM docs WHERE {where}
                    ORDER BY updated_at DESC LIMIT %s
                """, params + [min(limit, 100)])
                results = [dict(r) for r in cur.fetchall()]
        return {"ok": True, "query": query, "count": len(results), "results": results}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def list_docs(
    app_slug: str | None = None,
    category: str | None = None, tag: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """List docs with optional filters."""
    try:
        conditions = []
        params: list = []
        if app_slug: conditions.append("app_slug = %s"); params.append(app_slug)
        if category: conditions.append("category = %s"); params.append(category)
        if tag:      conditions.append("tags @> %s"); params.append(psycopg2.extras.Json([tag]))
        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute(f"""
                    SELECT id, title, slug, category, tags, app_slug, author, updated_at
                    FROM docs {where} ORDER BY updated_at DESC LIMIT %s
                """, params + [min(limit, 500)])
                docs = [dict(r) for r in cur.fetchall()]
        return {"ok": True, "count": len(docs), "docs": docs}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
