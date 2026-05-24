# mcp-redis

**Version:** 0.1.0 | **Runtime:** Python 3.12 | **Image:** `ghcr.io/chaghadi/mcp-redis`

Redis MCP for mmiri28 solutions — cache, queue, pub/sub.

---

## Tools

| Group | Tool | Description |
|-------|------|-------------|
| Health | `health_check()` | Ping Redis, return version |
| Cache | `cache_set(key, value, ttl_seconds)` | Set with optional TTL |
| Cache | `cache_get(key)` | Get value |
| Cache | `cache_delete(keys)` | Delete one or more keys |
| Cache | `cache_exists(key)` | Check existence |
| Cache | `cache_ttl(key)` | Remaining TTL in seconds |
| Cache | `cache_set_many(items, ttl_seconds)` | Batch set (pipeline) |
| Cache | `cache_get_many(keys)` | Batch get (pipeline) |
| Queue | `queue_push(queue_name, payload)` | Push job (FIFO) |
| Queue | `queue_pop(queue_name)` | Non-blocking pop |
| Queue | `queue_bpop(queue_name, timeout)` | Blocking pop |
| Queue | `queue_length(queue_name)` | Jobs waiting |
| Queue | `queue_peek(queue_name, count)` | Preview without consuming |
| Pub/Sub | `publish(channel, message)` | Publish to channel |
| Pub/Sub | `pubsub_channels(pattern)` | List active channels |
| Pub/Sub | `pubsub_numsub(channels)` | Subscriber counts |

---

## Setup

```powershell
cd data\mcp-redis
uv sync
copy .env.example .env
# Edit .env — add your Upstash REDIS_URL
uv run pytest tests/ -v
```

## Connecting to Upstash

1. Create a free database at upstash.com
2. Go to your database → Connect → .env tab
3. Copy `REDIS_URL` into your `.env`

## Key namespacing

All keys are automatically prefixed with `KEY_PREFIX` (default: `mmiri28`).
A call to `cache_set("session:abc", ...)` stores `mmiri28:session:abc`.
This prevents collisions when sharing a Redis instance across apps.

## Subscribe pattern (app code)

`subscribe()` is not an MCP tool — see ADR-0006. In your app:

```python
import redis, os
r = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
pubsub = r.pubsub()
pubsub.subscribe("mmiri28:events:user.created")
for message in pubsub.listen():
    if message["type"] == "message":
        handle(message["data"])
```
