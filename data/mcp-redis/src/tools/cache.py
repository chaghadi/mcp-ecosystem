"""
cache.py — Key-value cache tools.

Used by mcp-auth for session tokens and rate limit counters.
All keys are automatically namespaced with KEY_PREFIX to avoid collisions.
"""

import json
from typing import Any

import redis

from src.client import get_client
from src.config import settings


def _encode(value: Any) -> str:
    """Encode any Python value to a JSON string for storage."""
    return json.dumps(value)


def _decode(raw: str | None) -> Any:
    """Decode a stored JSON string back to a Python value."""
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw  # Return as-is if not valid JSON


def run_set(key: str, value: Any, ttl_seconds: int | None = None) -> dict[str, Any]:
    """
    Set a cache key to a value with an optional TTL.

    Args:
        key:         Cache key. Automatically prefixed with KEY_PREFIX.
        value:       Any JSON-serializable value.
        ttl_seconds: Expiry time in seconds. None = no expiry.

    Returns:
        ok, key (prefixed), ttl_seconds
    """
    try:
        client = get_client()
        prefixed = settings.prefixed(key)
        encoded = _encode(value)
        if ttl_seconds is not None:
            client.setex(prefixed, ttl_seconds, encoded)
        else:
            client.set(prefixed, encoded)
        return {"ok": True, "key": prefixed, "ttl_seconds": ttl_seconds}
    except redis.RedisError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_get(key: str) -> dict[str, Any]:
    """
    Get a cache value by key.

    Args:
        key: Cache key (without prefix — prefix is added automatically).

    Returns:
        ok, value (None if key does not exist), exists flag.
    """
    try:
        client = get_client()
        prefixed = settings.prefixed(key)
        raw = client.get(prefixed)
        return {
            "ok": True,
            "key": prefixed,
            "value": _decode(raw),
            "exists": raw is not None,
        }
    except redis.RedisError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_delete(*keys: str) -> dict[str, Any]:
    """
    Delete one or more cache keys.

    Args:
        keys: One or more keys to delete (without prefix).

    Returns:
        ok, deleted_count.
    """
    try:
        client = get_client()
        prefixed = [settings.prefixed(k) for k in keys]
        count = client.delete(*prefixed)
        return {"ok": True, "deleted_count": count, "keys": prefixed}
    except redis.RedisError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_exists(key: str) -> dict[str, Any]:
    """
    Check whether a cache key exists.

    Args:
        key: Cache key (without prefix).
    """
    try:
        client = get_client()
        prefixed = settings.prefixed(key)
        exists = bool(client.exists(prefixed))
        return {"ok": True, "key": prefixed, "exists": exists}
    except redis.RedisError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_ttl(key: str) -> dict[str, Any]:
    """
    Get the remaining TTL of a cache key in seconds.

    Returns:
        ttl_seconds: Remaining seconds. -1 = no expiry. -2 = key does not exist.
    """
    try:
        client = get_client()
        prefixed = settings.prefixed(key)
        ttl = client.ttl(prefixed)
        return {
            "ok": True,
            "key": prefixed,
            "ttl_seconds": ttl,
            "note": (
                "No expiry set." if ttl == -1 else
                "Key does not exist." if ttl == -2 else
                f"Expires in {ttl}s."
            ),
        }
    except redis.RedisError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_set_many(items: dict[str, Any], ttl_seconds: int | None = None) -> dict[str, Any]:
    """
    Set multiple cache keys in a single pipeline (atomic batch).

    Args:
        items:       Dict of key → value pairs.
        ttl_seconds: TTL applied to all keys. None = no expiry.

    Returns:
        ok, count of keys set.
    """
    try:
        client = get_client()
        pipe = client.pipeline()
        for key, value in items.items():
            prefixed = settings.prefixed(key)
            encoded = _encode(value)
            if ttl_seconds is not None:
                pipe.setex(prefixed, ttl_seconds, encoded)
            else:
                pipe.set(prefixed, encoded)
        pipe.execute()
        return {"ok": True, "set_count": len(items), "ttl_seconds": ttl_seconds}
    except redis.RedisError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_get_many(keys: list[str]) -> dict[str, Any]:
    """
    Get multiple cache values in a single pipeline.

    Args:
        keys: List of keys (without prefix).

    Returns:
        ok, results dict of key → value (None if missing).
    """
    try:
        client = get_client()
        prefixed = [settings.prefixed(k) for k in keys]
        values = client.mget(prefixed)
        results = {
            keys[i]: _decode(v)
            for i, v in enumerate(values)
        }
        return {
            "ok": True,
            "results": results,
            "hit_count": sum(1 for v in values if v is not None),
            "miss_count": sum(1 for v in values if v is None),
        }
    except redis.RedisError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}
