"""
schema.py — Database schema introspection tools.

list_tables()    — list all user tables in a schema.
describe_table() — columns, types, nullability, defaults, constraints.
"""

from typing import Any

import psycopg2
import psycopg2.extras

from src.db import get_connection


def run_list_tables(schema: str = "public") -> dict[str, Any]:
    """
    List all user-created tables in a PostgreSQL schema.

    Args:
        schema: Schema name (default: "public").

    Returns:
        tables: List of dicts with name, row_estimate, size.
    """
    sql = """
        SELECT
            t.table_name                                    AS name,
            pg_stat_get_live_tuples(c.oid)                  AS row_estimate,
            pg_size_pretty(pg_total_relation_size(c.oid))   AS total_size
        FROM information_schema.tables t
        JOIN pg_class c
          ON c.relname = t.table_name
        JOIN pg_namespace n
          ON n.oid = c.relnamespace AND n.nspname = t.table_schema
        WHERE t.table_schema = %s
          AND t.table_type = 'BASE TABLE'
        ORDER BY t.table_name;
    """
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, [schema])
                tables = [dict(r) for r in cur.fetchall()]
                return {
                    "ok": True,
                    "schema": schema,
                    "table_count": len(tables),
                    "tables": tables,
                }
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_describe_table(table_name: str, schema: str = "public") -> dict[str, Any]:
    """
    Describe a table's columns, types, constraints, and indexes.

    Args:
        table_name: Name of the table.
        schema:     Schema name (default: "public").

    Returns:
        columns:     List of column definitions.
        constraints: Primary keys, foreign keys, unique constraints.
        indexes:     Index definitions.
    """
    # ── Columns ───────────────────────────────────────────────────────────────
    col_sql = """
        SELECT
            c.column_name                                           AS name,
            c.data_type                                             AS type,
            c.character_maximum_length                              AS max_length,
            c.is_nullable                                           AS nullable,
            c.column_default                                        AS default,
            c.ordinal_position                                      AS position
        FROM information_schema.columns c
        WHERE c.table_schema = %s
          AND c.table_name   = %s
        ORDER BY c.ordinal_position;
    """

    # ── Constraints ───────────────────────────────────────────────────────────
    con_sql = """
        SELECT
            tc.constraint_name  AS name,
            tc.constraint_type  AS type,
            kcu.column_name     AS column,
            ccu.table_name      AS foreign_table,
            ccu.column_name     AS foreign_column
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema    = kcu.table_schema
        LEFT JOIN information_schema.constraint_column_usage ccu
          ON tc.constraint_name = ccu.constraint_name
         AND tc.table_schema    = ccu.table_schema
        WHERE tc.table_schema = %s
          AND tc.table_name   = %s
        ORDER BY tc.constraint_type, tc.constraint_name;
    """

    # ── Indexes ───────────────────────────────────────────────────────────────
    idx_sql = """
        SELECT
            indexname   AS name,
            indexdef    AS definition
        FROM pg_indexes
        WHERE schemaname = %s
          AND tablename  = %s
        ORDER BY indexname;
    """

    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(col_sql, [schema, table_name])
                columns = [dict(r) for r in cur.fetchall()]

                if not columns:
                    return {
                        "ok": False,
                        "error": (
                            f"Table '{schema}.{table_name}' not found. "
                            "Run list_tables to see available tables."
                        ),
                    }

                cur.execute(con_sql, [schema, table_name])
                constraints = [dict(r) for r in cur.fetchall()]

                cur.execute(idx_sql, [schema, table_name])
                indexes = [dict(r) for r in cur.fetchall()]

                return {
                    "ok": True,
                    "table": f"{schema}.{table_name}",
                    "column_count": len(columns),
                    "columns": columns,
                    "constraints": constraints,
                    "indexes": indexes,
                }
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}
