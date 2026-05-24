# ADR-0010: Separate Alembic Version Tables Per MCP

**Date:** 2026-05-24
**Status:** Accepted
**Author:** chaghadi (discovered and fixed by Claude Code)
**Brand:** mmiri28 solutions

---

## Context

All MCPs share the same Supabase PostgreSQL database. Alembic uses a
`alembic_version` table to track which migrations have been applied.
When multiple MCPs share one database, they all write to the same
`alembic_version` table by default.

This caused a silent bug: when mcp-user-mgmt ran its `0001` migration,
Alembic found revision `0001` already in `alembic_version` (written by
mcp-auth) and skipped mcp-user-mgmt's migration entirely.

## Decision

Every MCP with an Alembic migration must use its own version table.
Set `version_table` in **both** `context.configure()` calls in `migrations/env.py`.

**Naming convention:** `alembic_version_{mcp_name}`

| MCP | version_table |
|-----|---------------|
| mcp-postgres  | `alembic_version_postgres` |
| mcp-auth      | `alembic_version_auth` |
| mcp-user-mgmt | `alembic_version_user_mgmt` |
| mcp-billing   | `alembic_version_billing` |
| (future MCPs) | `alembic_version_{name}` |

## Consequences

- Migrations across all MCPs are fully independent
- One MCP's revision IDs never interfere with another's
- Every new MCP with migrations must follow this convention — enforced by template
