"""
queue.py — FIFO job queue tools using Redis Lists.

Used by mcp-notifications and mcp-billing for background job dispatch.

Design:
  LPUSH adds jobs to the head (left).
  RPOP / BRPOP removes jobs from the tail (right).
  This gives strict FIFO ordering.

Queue names are prefixed with KEY_PREFIX automatically.
"""

import json
from typing import Any

import redis

from src.client import get_client
from src.config import settings


def _queue_key(queue_name: str) -> str:
    return settings.prefixed(f"queue:{queue_name}")


def _encode(payload: Any) -> str:
    return json.dumps(payload)


def _decode(raw: str | None) -> Any:
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


def run_push(queue_name: str, payload: Any) -> dict[str, Any]:
    """
    Push a job onto the queue (LPUSH).

    Args:
        queue_name: Name of the queue (e.g. "email", "sms", "invoice").
        payload:    Any JSON-serializable value. Typically a dict with job details.

    Returns:
        ok, queue_key, queue_length after push.

    Example:
        queue_push("email", {"to": "ada@example.com", "template": "welcome"})
    """
    try:
        client = get_client()
        key = _queue_key(queue_name)
        length = client.lpush(key, _encode(payload))
        return {
            "ok": True,
            "queue": queue_name,
            "queue_key": key,
            "queue_length": length,
        }
    except redis.RedisError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_pop(queue_name: str) -> dict[str, Any]:
    """
    Pop the next job from the queue (non-blocking RPOP).

    Returns None payload if the queue is empty.

    Args:
        queue_name: Name of the queue.
    """
    try:
        client = get_client()
        key = _queue_key(queue_name)
        raw = client.rpop(key)
        return {
            "ok": True,
            "queue": queue_name,
            "payload": _decode(raw),
            "empty": raw is None,
        }
    except redis.RedisError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_bpop(queue_name: str, timeout: int = 5) -> dict[str, Any]:
    """
    Blocking pop — wait up to `timeout` seconds for a job (BRPOP).

    Useful for worker processes that should wait for work rather than polling.

    Args:
        queue_name: Name of the queue.
        timeout:    Max seconds to wait. 0 = wait forever. Default: 5.
    """
    try:
        client = get_client()
        key = _queue_key(queue_name)
        result = client.brpop(key, timeout=timeout)
        if result is None:
            return {
                "ok": True,
                "queue": queue_name,
                "payload": None,
                "empty": True,
                "timed_out": True,
            }
        _, raw = result
        return {
            "ok": True,
            "queue": queue_name,
            "payload": _decode(raw),
            "empty": False,
            "timed_out": False,
        }
    except redis.RedisError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_length(queue_name: str) -> dict[str, Any]:
    """
    Return the number of jobs currently in the queue (LLEN).

    Args:
        queue_name: Name of the queue.
    """
    try:
        client = get_client()
        key = _queue_key(queue_name)
        length = client.llen(key)
        return {
            "ok": True,
            "queue": queue_name,
            "queue_key": key,
            "length": length,
        }
    except redis.RedisError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_peek(queue_name: str, count: int = 10) -> dict[str, Any]:
    """
    Peek at the next jobs in the queue without removing them (LRANGE).

    Shows jobs in the order they will be processed (oldest first).

    Args:
        queue_name: Name of the queue.
        count:      Number of jobs to preview. Default: 10. Max: 100.
    """
    count = min(max(1, count), 100)
    try:
        client = get_client()
        key = _queue_key(queue_name)
        # LRANGE from tail (where RPOP takes from) to get processing order
        total = client.llen(key)
        items = client.lrange(key, -count, -1)
        items.reverse()  # oldest first
        return {
            "ok": True,
            "queue": queue_name,
            "total_length": total,
            "preview_count": len(items),
            "jobs": [_decode(item) for item in items],
        }
    except redis.RedisError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}
