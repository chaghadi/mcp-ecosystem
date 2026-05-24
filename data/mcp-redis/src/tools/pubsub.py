"""
pubsub.py — Pub/Sub tools using Redis PUBLISH / PUBSUB commands.

Used by mcp-webhooks and mcp-notifications for real-time event fan-out.

Design note:
  subscribe() is intentionally NOT an MCP tool — see ADR-0006.
  MCP is request/response. A blocking subscribe would hang the server.
  Apps that consume messages implement their own subscriber workers
  using redis-py directly with the pattern:

      import redis, os
      r = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
      pubsub = r.pubsub()
      pubsub.subscribe("mmiri28:events:user.created")
      for message in pubsub.listen():
          if message["type"] == "message":
              handle(message["data"])

  mcp-redis handles publishing and channel inspection only.
"""

import json
from typing import Any

import redis

from src.client import get_client
from src.config import settings


def _channel_key(channel: str) -> str:
    return settings.prefixed(f"events:{channel}")


def run_publish(channel: str, message: Any) -> dict[str, Any]:
    """
    Publish a message to a channel.

    All subscribers currently listening on this channel receive the message.
    If no subscribers are active, the message is dropped (Redis pub/sub is fire-and-forget).

    Args:
        channel: Channel name (e.g. "user.created", "payment.completed").
                 Automatically prefixed: mmiri28:events:{channel}
        message: Any JSON-serializable value.

    Returns:
        ok, channel_key, receiver_count (number of subscribers who received it).
    """
    try:
        client = get_client()
        channel_key = _channel_key(channel)
        encoded = json.dumps(message)
        receiver_count = client.publish(channel_key, encoded)
        return {
            "ok": True,
            "channel": channel,
            "channel_key": channel_key,
            "receiver_count": receiver_count,
            "note": (
                "Message delivered." if receiver_count > 0
                else "No active subscribers — message was dropped. "
                     "This is normal if no worker is running yet."
            ),
        }
    except redis.RedisError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_channels(pattern: str = "*") -> dict[str, Any]:
    """
    List active pub/sub channels (channels with at least one subscriber).

    Args:
        pattern: Glob pattern to filter channels. Default: all channels.
                 Example: "mmiri28:events:user.*"

    Returns:
        ok, channels list, count.
    """
    try:
        client = get_client()
        # Apply prefix to the pattern if not already present
        if not pattern.startswith(settings.key_prefix):
            full_pattern = settings.prefixed(f"events:{pattern}")
        else:
            full_pattern = pattern
        channels = client.pubsub_channels(full_pattern)
        return {
            "ok": True,
            "pattern": full_pattern,
            "channel_count": len(channels),
            "channels": sorted(channels),
        }
    except redis.RedisError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_numsub(*channels: str) -> dict[str, Any]:
    """
    Return the subscriber count for one or more channels.

    Args:
        channels: Channel names (without prefix). Pass multiple to check several at once.

    Returns:
        ok, dict of channel_key → subscriber_count.
    """
    try:
        client = get_client()
        channel_keys = [_channel_key(c) for c in channels]
        counts = client.pubsub_numsub(*channel_keys)
        return {
            "ok": True,
            "subscribers": {
                ch: count for ch, count in counts.items()
            },
        }
    except redis.RedisError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}
