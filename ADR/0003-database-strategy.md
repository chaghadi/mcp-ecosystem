# ADR-0003: Database Strategy — Supabase Now, DigitalOcean Later

**Date:** 2026-05-24
**Status:** Accepted
**Author:** chaghadi
**Brand:** mmiri28 solutions

---

## Context

We needed a PostgreSQL host that is:
- Free or very low cost while building
- Always-on (desktop as a server is unreliable for production)
- Easy to migrate away from when costs grow
- Not locked in to a vendor-specific SDK or feature set

## Decision

**Phase 1 (now):** Supabase free tier.
**Phase 2 (production):** DigitalOcean Managed PostgreSQL.

The swap is exactly one env var change: `DATABASE_URL`.

**Rules that make migration trivial:**
- `mcp-postgres` uses standard `psycopg2` only — no Supabase SDK, no Supabase-specific APIs
- No Supabase Auth, Supabase Storage, or Supabase Realtime — those are handled by dedicated MCPs
- All schema changes go through Alembic migrations — never manual edits in the Supabase dashboard
- `DATABASE_URL` format is identical for Supabase and DigitalOcean:
  `postgresql://user:pass@host:port/db`

**What goes on Supabase / public cloud:**
- Only structured relational data that the app actively queries
- No media files, no logs, no bulk exports — those go to `mcp-storage`

## Consequences

- Any developer can swap the database host in under 5 minutes
- The Supabase dashboard is never the source of truth — migrations are
- When DigitalOcean costs less than Supabase at scale, migration is a one-liner
