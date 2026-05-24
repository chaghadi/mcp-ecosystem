"""
server.py — mcp-redis MCP server entry point.

Tools:
  Cache:   cache_set, cache_get, cache_delete, cache_exists, cache_ttl,
           cache_set_many, cache_get_many
  Queue:   queue_push, queue_pop, queue_bpop, queue_length, queue_peek
  Pub/Sub: publish, pubsub_channels, pubsub_numsub
  Health:  health_check
"""

from mcp.server.fastmcp import FastMCP
from typing import Any

from src.tools import cache as _cache
from src.tools import health as _health
from src.tools import pubsub as _pubsub
from src.tools import queue as _queue

mcp = FastMCP(
    "mcp-redis",
    instructions=(
        "Redis MCP for mmiri28 solutions. "
        "Cache (sessions, rate limits), Queue (background jobs), "
        "Pub/Sub (event fan-out). Swap REDIS_URL to move between Upstash and DigitalOcean."
    ),
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Health
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
def health_check() -> dict:
    """Ping Redis and return version and connection status."""
    return _health.run()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Cache
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
def cache_set(key: str, value: Any, ttl_seconds: int | None = None) -> dict:
    """
    Set a cache key to a value with optional TTL.

    Keys are namespaced automatically with KEY_PREFIX.
    Value can be any JSON-serializable type (str, int, dict, list, bool).

    Args:
        key:         Cache key.
        value:       Value to store.
        ttl_seconds: Seconds until expiry. None = no expiry.
    """
    return _cache.run_set(key=key, value=value, ttl_seconds=ttl_seconds)


@mcp.tool()
def cache_get(key: str) -> dict:
    """
    Get a cached value by key. Returns null value if key does not exist.

    Args:
        key: Cache key (without prefix).
    """
    return _cache.run_get(key=key)


@mcp.tool()
def cache_delete(keys: list[str]) -> dict:
    """
    Delete one or more cache keys.

    Args:
        keys: List of keys to delete (without prefix).
    """
    return _cache.run_delete(*keys)


@mcp.tool()
def cache_exists(key: str) -> dict:
    """
    Check whether a cache key exists.

    Args:
        key: Cache key (without prefix).
    """
    return _cache.run_exists(key=key)


@mcp.tool()
def cache_ttl(key: str) -> dict:
    """
    Get remaining TTL of a key in seconds.
    Returns -1 if no expiry, -2 if key does not exist.

    Args:
        key: Cache key (without prefix).
    """
    return _cache.run_ttl(key=key)


@mcp.tool()
def cache_set_many(items: dict[str, Any], ttl_seconds: int | None = None) -> dict:
    """
    Set multiple keys in a single atomic pipeline.

    Args:
        items:       Dict of key → value pairs.
        ttl_seconds: TTL applied to all keys.
    """
    return _cache.run_set_many(items=items, ttl_seconds=ttl_seconds)


@mcp.tool()
def cache_get_many(keys: list[str]) -> dict:
    """
    Get multiple keys in a single pipeline.

    Args:
        keys: List of keys (without prefix).

    Returns hit_count, miss_count, and results dict.
    """
    return _cache.run_get_many(keys=keys)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Queue
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
def queue_push(queue_name: str, payload: Any) -> dict:
    """
    Push a job onto a FIFO queue.

    Args:
        queue_name: Queue name (e.g. "email", "sms", "invoice").
        payload:    Job data — any JSON-serializable value.

    Example:
        queue_push("email", {"to": "ada@example.com", "template": "welcome"})
    """
    return _queue.run_push(queue_name=queue_name, payload=payload)


@mcp.tool()
def queue_pop(queue_name: str) -> dict:
    """
    Pop the next job from the queue (non-blocking).
    Returns empty=true if the queue has no jobs.

    Args:
        queue_name: Queue name.
    """
    return _queue.run_pop(queue_name=queue_name)


@mcp.tool()
def queue_bpop(queue_name: str, timeout: int = 5) -> dict:
    """
    Blocking pop — wait up to timeout seconds for a job.
    Returns timed_out=true if no job arrived within the timeout.

    Args:
        queue_name: Queue name.
        timeout:    Max seconds to wait. 0 = wait forever. Default: 5.
    """
    return _queue.run_bpop(queue_name=queue_name, timeout=timeout)


@mcp.tool()
def queue_length(queue_name: str) -> dict:
    """
    Return the number of jobs currently waiting in a queue.

    Args:
        queue_name: Queue name.
    """
    return _queue.run_length(queue_name=queue_name)


@mcp.tool()
def queue_peek(queue_name: str, count: int = 10) -> dict:
    """
    Preview the next jobs in a queue without removing them.
    Shows jobs in processing order (oldest first). Max 100.

    Args:
        queue_name: Queue name.
        count:      Number of jobs to preview. Default: 10.
    """
    return _queue.run_peek(queue_name=queue_name, count=count)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pub/Sub
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
def publish(channel: str, message: Any) -> dict:
    """
    Publish a message to a channel.

    All active subscribers receive the message instantly.
    If no subscribers are listening, the message is dropped (fire-and-forget).

    Args:
        channel: Event channel (e.g. "user.created", "payment.completed").
                 Auto-prefixed to: {KEY_PREFIX}:events:{channel}
        message: Any JSON-serializable value.
    """
    return _pubsub.run_publish(channel=channel, message=message)


@mcp.tool()
def pubsub_channels(pattern: str = "*") -> dict:
    """
    List active pub/sub channels (channels with at least one subscriber).

    Args:
        pattern: Glob pattern. Default: all channels.
    """
    return _pubsub.run_channels(pattern=pattern)


@mcp.tool()
def pubsub_numsub(channels: list[str]) -> dict:
    """
    Return subscriber count for one or more channels.

    Args:
        channels: List of channel names (without prefix).
    """
    return _pubsub.run_numsub(*channels)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Entry point
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
