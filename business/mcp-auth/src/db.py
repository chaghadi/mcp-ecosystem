"""db.py — PostgreSQL connection for mcp-auth."""

from contextlib import contextmanager
from typing import Generator

import psycopg2
import psycopg2.extras

from src.config import settings


@contextmanager
def get_conn() -> Generator[psycopg2.extensions.connection, None, None]:
    """Open a connection, commit on success, rollback on error."""
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set.")
    conn = psycopg2.connect(settings.database_url)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def dict_cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
