# mcp-redis Changelog

## [0.1.0] — 2026-05-24 — chaghadi

**Initial build. mmiri28 solutions.**

### Added
**Cache:** `cache_set`, `cache_get`, `cache_delete`, `cache_exists`,
`cache_ttl`, `cache_set_many`, `cache_get_many`

**Queue:** `queue_push`, `queue_pop`, `queue_bpop`, `queue_length`, `queue_peek`

**Pub/Sub:** `publish`, `pubsub_channels`, `pubsub_numsub`

**Health:** `health_check`

### Architecture decisions recorded
- ADR-0006: Redis Strategy (Upstash now, DigitalOcean later)

### Notes
- All keys namespaced with `KEY_PREFIX` (default: `mmiri28`)
- `subscribe()` intentionally not an MCP tool — see ADR-0006
- Tests use `fakeredis` — no live Redis needed to run the test suite
- Docker image: `ghcr.io/chaghadi/mcp-redis`
-e 
## [0.1.1] — 2026-05-24 — chaghadi

### Fixed
- FastMCP constructor: replaced invalid `description=` with `instructions=`
