"""server.py — mcp-search MCP server entry point."""

import subprocess
from mcp.server.fastmcp import FastMCP
from src.config import settings
from src.db import get_conn
from src.tools.search_tools import run_index, run_search, run_delete, run_reindex

mcp = FastMCP(
    "mcp-search",
    instructions="Full-text search MCP for mmiri28 solutions. Postgres tsvector — no extra infrastructure. Index, search, delete, reindex.",
)


@mcp.tool()
def health_check() -> dict:
    error = settings.validate()
    if error:
        return {"ok": False, "error": error}
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM search_index")
                count = cur.fetchone()[0]
        return {"ok": True, "status": "connected", "indexed_documents": count}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def run_migrations() -> dict:
    """Create the search_index table."""
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        capture_output=True, text=True, cwd=str(settings.mcp_root),
    )
    if result.returncode != 0:
        return {"ok": False, "error": result.stderr or result.stdout}
    return {"ok": True, "output": result.stdout or "Migrations applied."}


@mcp.tool()
def index_document(
    doc_id: str, content: str, app_slug: str,
    title: str = "", metadata: dict | None = None, language: str = "english",
) -> dict:
    """
    Add or update a document in the search index.

    Args:
        doc_id:   Your document ID (e.g. product UUID, article slug).
        content:  Text to index — concatenate title + body + tags.
        app_slug: App namespace.
        title:    Optional title (weighted higher in results).
        metadata: Extra data returned with results (url, type, thumbnail, etc.)
        language: Postgres FTS language. Default: "english".
    """
    return run_index(doc_id=doc_id, content=content, app_slug=app_slug,
                     title=title, metadata=metadata, language=language)


@mcp.tool()
def search(
    query: str, app_slug: str,
    limit: int = 20, metadata_filters: dict | None = None, language: str = "english",
) -> dict:
    """
    Full-text search with relevance ranking and excerpts.

    Args:
        query:            Search terms.
        app_slug:         Search within this app.
        limit:            Max results (default 20, max 100).
        metadata_filters: Filter by metadata fields e.g. {"type": "product"}.
        language:         FTS language. Default: "english".
    """
    return run_search(query=query, app_slug=app_slug, limit=limit,
                      metadata_filters=metadata_filters, language=language)


@mcp.tool()
def delete_document(doc_id: str, app_slug: str) -> dict:
    """Remove a document from the search index."""
    return run_delete(doc_id=doc_id, app_slug=app_slug)


@mcp.tool()
def reindex_app(app_slug: str, language: str = "english") -> dict:
    """Rebuild search vectors for all documents in an app."""
    return run_reindex(app_slug=app_slug, language=language)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
