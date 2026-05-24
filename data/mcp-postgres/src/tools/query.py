"""
query.py — SQL query and execute tools.

query()   — SELECT queries, returns rows as list of dicts.
execute() — INSERT / UPDATE / DELETE, returns affected row count.

Both use parameterized queries — never string-format SQL with user input.
"""

from typing import Any

import psycopg2
import psycopg2.extras

from src.db import get_connection


def run_query(sql: str, params: list | None = None) -> dict[str, Any]:
    """
    Execute a SELECT query and return all rows as a list of dicts.

    Args:
        sql:    A SELECT statement. Use %s placeholders for parameters.
        params: Optional list of values to bind to placeholders.

    Returns:
        rows:       List of row dicts.
        row_count:  Number of rows returned.

    Example:
        query("SELECT * FROM users WHERE active = %s", [True])
    """
    if not sql or not sql.strip():
        return {"error": "sql cannot be empty."}

    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params or [])
                rows = [dict(r) for r in cur.fetchall()]
                return {
                    "ok": True,
                    "rows": rows,
                    "row_count": len(rows),
                }
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_execute(sql: str, params: list | None = None) -> dict[str, Any]:
    """
    Execute an INSERT, UPDATE, or DELETE statement.

    Args:
        sql:    A DML statement. Use %s placeholders for parameters.
                Add RETURNING to get back affected rows.
        params: Optional list of values to bind to placeholders.

    Returns:
        affected_rows:  Number of rows affected.
        returned_rows:  Rows from a RETURNING clause, if present.

    Example:
        execute(
            "INSERT INTO users (email, name) VALUES (%s, %s) RETURNING id",
            ["ada@example.com", "Ada"]
        )
    """
    if not sql or not sql.strip():
        return {"error": "sql cannot be empty."}

    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params or [])
                affected = cur.rowcount
                returned: list[dict] = []
                # Only fetch if the statement had RETURNING
                if cur.description is not None:
                    returned = [dict(r) for r in cur.fetchall()]
                return {
                    "ok": True,
                    "affected_rows": affected,
                    "returned_rows": returned,
                }
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}
