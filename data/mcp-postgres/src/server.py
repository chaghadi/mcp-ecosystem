"""
server.py — mcp-postgres MCP server entry point.

Tools:
  health_check()                       — connectivity check
  query(sql, params)                   — SELECT, returns rows as dicts
  execute(sql, params)                 — INSERT / UPDATE / DELETE
  list_tables(schema)                  — list tables in a schema
  describe_table(table_name, schema)   — columns, constraints, indexes
  migrate_up(target)                   — run pending Alembic migrations
  migrate_status()                     — current revision + pending
  create_migration(name)               — create a new migration file
"""

from mcp.server.fastmcp import FastMCP

from src.tools import health as _health
from src.tools import migrate as _migrate
from src.tools import query as _query
from src.tools import schema as _schema

mcp = FastMCP(
    "mcp-postgres",
    description=(
        "PostgreSQL MCP for mmiri28 solutions. "
        "Handles queries, schema introspection, and Alembic migrations. "
        "Swap DATABASE_URL to move between Supabase and DigitalOcean."
    ),
)


# ── Connectivity ─────────────────────────────────────────────────────────────

@mcp.tool()
def health_check() -> dict:
    """
    Check database connectivity. Runs SELECT version() and returns status.
    Safe to call any time — does not modify data.
    """
    return _health.run()


# ── Queries ───────────────────────────────────────────────────────────────────

@mcp.tool()
def query(sql: str, params: list | None = None) -> dict:
    """
    Execute a SELECT query and return rows as a list of dicts.

    Use %s placeholders for parameters — never format SQL with f-strings.

    Args:
        sql:    SELECT statement with %s placeholders.
        params: Values to bind (optional).

    Example:
        query("SELECT * FROM users WHERE active = %s", [True])
    """
    return _query.run_query(sql=sql, params=params)


@mcp.tool()
def execute(sql: str, params: list | None = None) -> dict:
    """
    Execute an INSERT, UPDATE, or DELETE statement.

    Use %s placeholders for parameters. Add RETURNING to get back rows.

    Args:
        sql:    DML statement with %s placeholders.
        params: Values to bind (optional).

    Example:
        execute(
            "INSERT INTO users (email) VALUES (%s) RETURNING id",
            ["ada@example.com"]
        )
    """
    return _query.run_execute(sql=sql, params=params)


# ── Schema introspection ──────────────────────────────────────────────────────

@mcp.tool()
def list_tables(schema: str = "public") -> dict:
    """
    List all user-created tables in a PostgreSQL schema.

    Args:
        schema: Schema name (default: "public").

    Returns table names, row estimates, and sizes.
    """
    return _schema.run_list_tables(schema=schema)


@mcp.tool()
def describe_table(table_name: str, schema: str = "public") -> dict:
    """
    Describe a table: columns, types, nullability, defaults, constraints, indexes.

    Args:
        table_name: Name of the table.
        schema:     Schema name (default: "public").
    """
    return _schema.run_describe_table(table_name=table_name, schema=schema)


# ── Migrations ────────────────────────────────────────────────────────────────

@mcp.tool()
def migrate_up(target: str = "head") -> dict:
    """
    Run pending Alembic migrations.

    Args:
        target: Revision to upgrade to. Default "head" runs all pending.

    Always run migrate_status() first to see what will be applied.
    Per ADR-0005: forward-only, no rollbacks.
    """
    return _migrate.run_migrate_up(target=target)


@mcp.tool()
def migrate_status() -> dict:
    """
    Show the current Alembic revision and pending migrations.

    Run this before migrate_up() to preview what will be applied.
    """
    return _migrate.run_migrate_status()


@mcp.tool()
def create_migration(name: str) -> dict:
    """
    Create a new Alembic migration file in migrations/versions/.

    Args:
        name: Short verb-phrase description: "add_users_table", "add_email_index".

    After creation: open the file, write your SQL in upgrade(), leave downgrade() empty.
    Then call migrate_up() to apply it.
    """
    return _migrate.run_create_migration(name=name)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
