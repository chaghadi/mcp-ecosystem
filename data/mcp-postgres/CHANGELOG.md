# mcp-postgres Changelog

## [0.1.0] — 2026-05-24 — chaghadi

**Initial build. mmiri28 solutions.**

### Added
- `health_check` — connectivity check, returns PostgreSQL version
- `query` — parameterized SELECT, returns rows as list of dicts
- `execute` — parameterized INSERT/UPDATE/DELETE with optional RETURNING
- `list_tables` — list all user tables in a schema with size and row estimates
- `describe_table` — full column definitions, constraints, and indexes
- `migrate_up` — run pending Alembic migrations (forward-only per ADR-0005)
- `migrate_status` — current revision + pending migrations
- `create_migration` — create a new Alembic migration file

### Architecture decisions recorded
- ADR-0003: Database Strategy (Supabase now, DigitalOcean later)
- ADR-0004: Docker images in GitHub Container Registry
- ADR-0005: Migration strategy (Alembic, forward-only, small)

### Notes
- `DATABASE_URL` is the only config needed — same format for Supabase and DO
- Live DB tests are skipped automatically when `DATABASE_URL` is not set
- Docker image: `ghcr.io/chaghadi/mcp-postgres`
-e 
## [0.1.1] — 2026-05-24 — chaghadi

### Fixed
- FastMCP constructor: replaced invalid `description=` with `instructions=`
