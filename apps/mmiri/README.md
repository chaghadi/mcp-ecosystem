# mmiri

Validation app for the mmiri28 MCP ecosystem.

A static HTML banner page backed by a small FastAPI service that calls
`mcp-analytics` at runtime to record visits and surface counts. Proves that:

1. The ecosystem repo can host applications, not just MCPs (structural validation).
2. An app can spawn MCPs as subprocesses, send JSON-RPC tool calls over stdio,
   and use the responses to drive UI (runtime validation).
3. Credentials live only in MCPs, never in apps — `apps/mmiri/.env` is empty,
   while `business/mcp-analytics/.env` holds the DATABASE_URL.

## Run

```bash
cd apps/mmiri
uv sync
uv run mmiri
```

Visit http://localhost:8080.

## How it works

The FastAPI lifespan spawns `mcp-analytics` as a subprocess via stdio and
keeps the JSON-RPC session open for the lifetime of the app. Each `GET /`
results in a `track_event` call to the MCP, which writes to the shared
Supabase Postgres database. The bottom-left status panel polls
`/api/visit-count` and `/api/health` every 8 seconds to show the live state.

```
Browser ──HTTP──> mmiri (FastAPI) ──MCP/stdio──> mcp-analytics ──psycopg2──> Supabase
```

## Files

- `src/main.py` — FastAPI app with lifespan-managed MCP clients
- `src/mcp_client.py` — generic MCP client wrapper (reusable for other apps)
- `src/static/` — HTML and CSS for the banner

## Why this validates the architecture

The runtime architecture diagram in `mmiri28-mcp-ecosystem.pdf` shows apps
calling MCPs which in turn call external services. mmiri is the smallest
possible app that performs this exact flow end-to-end with real credentials
and a real database. If `uv run mmiri` works and the visit counter increments,
the architecture is real, not just documentation.
