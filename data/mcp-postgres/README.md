# mcp-postgres

**Version:** 0.1.0
**Runtime:** Python 3.12
**Transport:** stdio
**Image:** `ghcr.io/chaghadi/mcp-postgres`

PostgreSQL MCP for mmiri28 solutions.
Handles queries, schema introspection, and Alembic migrations.

---

## Tools

| Tool | Description |
|------|-------------|
| `health_check()` | Connectivity check, returns PostgreSQL version |
| `query(sql, params)` | SELECT — returns rows as list of dicts |
| `execute(sql, params)` | INSERT / UPDATE / DELETE with optional RETURNING |
| `list_tables(schema)` | List tables with size and row estimates |
| `describe_table(table_name, schema)` | Columns, constraints, indexes |
| `migrate_up(target)` | Run pending Alembic migrations |
| `migrate_status()` | Current revision + pending |
| `create_migration(name)` | Create a new migration file |

---

## Setup

```powershell
cd data\mcp-postgres
uv sync
copy .env.example .env
# Edit .env — add your Supabase DATABASE_URL
uv run pytest tests/ -v
```

---

## Connecting to Supabase

1. Go to your Supabase project → Settings → Database
2. Copy the **URI** under "Connection string"
3. Paste it as `DATABASE_URL` in your `.env`

```
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

Run `health_check()` to confirm the connection.

---

## Running migrations

```
migrate_status()              # see what's pending
migrate_up()                  # apply all pending
create_migration("add_users") # create a new migration file
```

Migration files live in `migrations/versions/`.
Write your SQL in `upgrade()`. Leave `downgrade()` empty (see ADR-0005).

---

## Migrating to DigitalOcean

Change one line in `.env`:

```
DATABASE_URL=postgresql://doadmin:[PASSWORD]@[HOST]:25060/defaultdb?sslmode=require
```

Run `health_check()` to confirm. Run `migrate_up()` to apply any pending migrations.
No code changes required.

---

## Dependencies

```
mcp[cli]>=1.0.0
psycopg2-binary>=2.9.0
alembic>=1.13.0
sqlalchemy>=2.0.0
python-dotenv>=1.0.0
```
