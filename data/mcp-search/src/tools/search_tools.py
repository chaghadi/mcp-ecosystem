"""
search_tools.py — Full-text search using Postgres tsvector.

index()    — add or update a document in the search index
search()   — full-text search with ranking
delete()   — remove a document from the index
reindex()  — rebuild tsvector for all docs in an app
"""

import uuid
from datetime import datetime, timezone
from typing import Any

import psycopg2
import psycopg2.extras

from src.db import dict_cursor, get_conn


def run_index(
    doc_id: str,
    content: str,
    app_slug: str,
    title: str = "",
    metadata: dict | None = None,
    language: str = "english",
) -> dict[str, Any]:
    """
    Add or update a document in the search index.

    Upserts by (app_slug, doc_id). Call this whenever a document is
    created or updated in your app.

    Args:
        doc_id:   Your document's ID (e.g. product UUID, article slug).
        content:  Text content to index (title + body + tags concatenated).
        app_slug: Which app this document belongs to.
        title:    Optional title — weighted higher in search.
        metadata: Extra data returned with results (e.g. url, type, thumbnail).
        language: Postgres text search language. Default: "english".
    """
    if not content or not content.strip():
        return {"ok": False, "error": "content cannot be empty."}

    now = datetime.now(timezone.utc)
    meta = psycopg2.extras.Json(metadata or {})

    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    INSERT INTO search_index
                        (id, doc_id, app_slug, title, content, metadata,
                         search_vector, created_at, updated_at)
                    VALUES (
                        %s, %s, %s, %s, %s, %s,
                        to_tsvector(%s, %s || ' ' || %s),
                        %s, %s
                    )
                    ON CONFLICT (app_slug, doc_id) DO UPDATE SET
                        title        = EXCLUDED.title,
                        content      = EXCLUDED.content,
                        metadata     = EXCLUDED.metadata,
                        search_vector = to_tsvector(%s, EXCLUDED.content || ' ' || EXCLUDED.title),
                        updated_at   = EXCLUDED.updated_at
                """, [
                    str(uuid.uuid4()), doc_id, app_slug, title, content, meta,
                    language, content, title,
                    now, now,
                    language,
                ])
        return {"ok": True, "doc_id": doc_id, "app_slug": app_slug}
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_search(
    query: str,
    app_slug: str,
    limit: int = 20,
    metadata_filters: dict | None = None,
    language: str = "english",
) -> dict[str, Any]:
    """
    Full-text search across indexed documents for an app.

    Results are ranked by relevance (ts_rank).

    Args:
        query:            Search query string.
        app_slug:         Search within this app's documents only.
        limit:            Max results. Default: 20. Max: 100.
        metadata_filters: Filter by metadata fields (e.g. {"type": "product"}).
        language:         Postgres text search language.
    """
    query = query.strip()
    if len(query) < 2:
        return {"ok": False, "error": "query must be at least 2 characters."}

    limit = min(max(1, limit), 100)

    # Convert query to tsquery — handle multi-word queries
    ts_query = " & ".join(query.split())

    conditions = ["app_slug = %s", "search_vector @@ to_tsquery(%s, %s)"]
    params: list = [app_slug, language, ts_query]

    if metadata_filters:
        for key, val in metadata_filters.items():
            conditions.append("metadata ->> %s = %s")
            params.extend([key, str(val)])

    where = " AND ".join(conditions)

    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute(f"""
                    SELECT
                        doc_id, title, app_slug, metadata,
                        ts_rank(search_vector, to_tsquery(%s, %s)) AS rank,
                        ts_headline(%s, content, to_tsquery(%s, %s),
                            'MaxWords=20, MinWords=10, ShortWord=3') AS excerpt,
                        updated_at
                    FROM search_index
                    WHERE {where}
                    ORDER BY rank DESC
                    LIMIT %s
                """, [language, ts_query, language, language, ts_query] + params + [limit])
                results = [dict(r) for r in cur.fetchall()]
        return {
            "ok": True, "query": query, "app_slug": app_slug,
            "result_count": len(results), "results": results,
        }
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_delete(doc_id: str, app_slug: str) -> dict[str, Any]:
    """Remove a document from the search index."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute(
                    "DELETE FROM search_index WHERE doc_id = %s AND app_slug = %s",
                    [doc_id, app_slug]
                )
                removed = cur.rowcount > 0
        return {"ok": True, "doc_id": doc_id, "app_slug": app_slug, "removed": removed}
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_reindex(app_slug: str, language: str = "english") -> dict[str, Any]:
    """Rebuild tsvector for all documents in an app (e.g. after language change)."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    UPDATE search_index
                    SET search_vector = to_tsvector(%s, content || ' ' || title),
                        updated_at = NOW()
                    WHERE app_slug = %s
                """, [language, app_slug])
                count = cur.rowcount
        return {"ok": True, "app_slug": app_slug, "reindexed": count}
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}
