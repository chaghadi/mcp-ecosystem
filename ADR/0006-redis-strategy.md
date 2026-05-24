# ADR-0006: Redis Strategy — Upstash Now, DigitalOcean Later

**Date:** 2026-05-24
**Status:** Accepted
**Author:** chaghadi
**Brand:** mmiri28 solutions

---

## Context

Redis serves three distinct purposes across the ecosystem:
- **Cache** — session tokens, rate limit counters, query results (`mcp-auth`)
- **Queue** — background job dispatch (`mcp-notifications`, `mcp-billing`)
- **Pub/Sub** — real-time event fan-out (`mcp-webhooks`, `mcp-notifications`)

We needed a Redis host that is free while building and easy to migrate away from.

## Decision

**Phase 1 (now):** Upstash free tier (serverless Redis, TLS, persistent).
**Phase 2 (production):** DigitalOcean Managed Redis.

The swap is one env var: `REDIS_URL`.

**Rules:**
- `mcp-redis` uses `redis-py` only — no Upstash SDK, no vendor-specific APIs
- `REDIS_URL` format works identically for Upstash and DigitalOcean:
  `rediss://default:password@hostname:port` (TLS)
- All three capabilities (cache, queue, pub/sub) live in one MCP
- Apps never connect to Redis directly — all Redis operations go through `mcp-redis`

**Subscribe note:**
`subscribe()` is intentionally not an MCP tool. MCP is request/response — a
blocking subscribe would hang the server. Apps that need to consume pub/sub
messages do so in their own worker process using `redis-py` directly.
`mcp-redis` handles `publish()` and channel introspection only.

## Consequences

- One `REDIS_URL` change migrates between Upstash and DigitalOcean
- Cache, queue, and pub/sub all share one connection config
- Subscribe consumers live in app code, not in the MCP layer
