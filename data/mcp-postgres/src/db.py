"""
db.py — Database connection management for mcp-postgres.

Provides a simple context manager for psycopg2 connections.
Each tool call opens and closes its own connection — no persistent pool
needed for a local stdio MCP process.
"""

from contextlib import contextmanager
from typing import Generator

import psycopg2
import psycopg2.extras

from src.config import settings


@contextmanager
def get_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    """
    Open a psycopg2 connection, yield it, commit on success, rollback on error.

    Usage:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT 1")

    Raises:
        RuntimeError: if DATABASE_URL is not configured.
        psycopg2.OperationalError: if the database cannot be reached.
    """
    error = settings.validate()
    if error:
        raise RuntimeError(error)

    conn = psycopg2.connect(settings.database_url)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def check_connectivity() -> dict:
    """
    Try to connect and run SELECT 1. Return status dict.
    Does not raise — callers check the 'ok' key.
    """
    error = settings.validate()
    if error:
        return {"ok": False, "error": error}

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version()")
                version = cur.fetchone()[0]
        return {"ok": True, "version": version}
    except psycopg2.OperationalError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": f"Unexpected error: {exc}"}
