"""
client.py — Redis connection factory for mcp-redis.

Each tool call creates a fresh connection from the URL.
No persistent pool needed for a local stdio MCP process.
"""

import redis
from src.config import settings


def get_client() -> redis.Redis:
    """
    Return a Redis client from REDIS_URL.

    Raises RuntimeError if REDIS_URL is not configured.
    Raises redis.ConnectionError if the server cannot be reached.
    """
    error = settings.validate()
    if error:
        raise RuntimeError(error)

    return redis.from_url(
        settings.redis_url,
        decode_responses=True,   # always return str, not bytes
        socket_connect_timeout=5,
        socket_timeout=5,
    )


def check_connectivity() -> dict:
    """Ping Redis. Returns status dict — never raises."""
    error = settings.validate()
    if error:
        return {"ok": False, "error": error}
    try:
        client = get_client()
        info = client.info("server")
        return {
            "ok": True,
            "redis_version": info.get("redis_version"),
            "mode": info.get("redis_mode", "standalone"),
        }
    except redis.RedisError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}
