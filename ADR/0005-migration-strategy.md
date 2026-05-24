# ADR-0005: Migration Strategy — Alembic, Forward-Only, Small

**Date:** 2026-05-24
**Status:** Accepted
**Author:** chaghadi
**Brand:** mmiri28 solutions

---

## Context

Schema changes need to be tracked, repeatable, and fast to apply.
We need a tool that works with any standard PostgreSQL host.

## Decision

**Tool:** Alembic (Python, SQLAlchemy-based). Industry standard, works with
Supabase and DigitalOcean PostgreSQL identically.

**Three rules for every migration:**

**1. Forward-only.**
`downgrade()` functions are left empty. Rollbacks are handled by writing a new
forward migration that undoes the change — not by running downgrade.
Reason: downgrade on production data is dangerous and rarely works cleanly.
Fast recovery = write a fix migration, apply it forward.

**2. Keep migrations small.**
One concern per migration file. "Add users table" is one file.
"Add users table and posts table and comments table" is three files.
Small migrations are faster to review, easier to debug, and safer to apply.

**3. Never edit a migration that has been applied to any environment.**
Once a migration has run on Supabase (even dev), it is frozen.
Create a new migration to amend it.

**Migration naming:**
`{revision}_{short_description}.py` — Alembic auto-generates the revision prefix.
Description should be a verb phrase: `add_users_table`, `add_email_index_to_users`.

**Running migrations:**
Via `mcp-postgres` tool: `migrate_up()` — runs `alembic upgrade head`.
Never run alembic directly in production; always go through the MCP gate.

## Consequences

- Any developer can apply all pending migrations with one tool call
- Migration history is the single source of truth for schema state
- Fast migrations: each migration is small, targeted, and pre-tested
- No surprise rollbacks destroying data
