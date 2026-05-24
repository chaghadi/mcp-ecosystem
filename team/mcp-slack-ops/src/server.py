"""server.py — mcp-slack-ops MCP server entry point."""

import httpx
from typing import Any
from mcp.server.fastmcp import FastMCP
from src.config import settings

mcp = FastMCP(
    "mcp-slack-ops",
    instructions="Slack MCP for mmiri28 solutions. Send messages, manage channels, list users, react to messages.",
)


def _post(method: str, body: dict) -> dict[str, Any]:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        r = httpx.post(f"{settings.base_url}/{method}",
                       headers=settings.headers, json=body, timeout=15)
        data = r.json()
        if data.get("ok"):
            return {"ok": True, "data": data}
        return {"ok": False, "error": data.get("error", "unknown")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _get(method: str, params: dict | None = None) -> dict[str, Any]:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        r = httpx.get(f"{settings.base_url}/{method}",
                      headers=settings.headers, params=params or {}, timeout=15)
        data = r.json()
        if data.get("ok"):
            return {"ok": True, "data": data}
        return {"ok": False, "error": data.get("error", "unknown")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def health_check() -> dict:
    """Verify Slack bot token and return workspace info."""
    result = _get("auth.test")
    if result["ok"]:
        d = result["data"]
        return {"ok": True, "team": d.get("team"), "bot_user": d.get("user"),
                "team_id": d.get("team_id")}
    return result


@mcp.tool()
def send_message(
    channel: str, text: str,
    thread_ts: str | None = None,
    blocks: list | None = None,
) -> dict[str, Any]:
    """
    Send a message to a Slack channel.

    Args:
        channel:    Channel name (e.g. "#general") or ID (e.g. "C12345").
        text:       Message text. Supports Slack markdown.
        thread_ts:  Reply to a thread (parent message timestamp).
        blocks:     Optional Block Kit blocks for rich formatting.
    """
    body: dict = {"channel": channel, "text": text}
    if thread_ts: body["thread_ts"] = thread_ts
    if blocks:    body["blocks"] = blocks
    result = _post("chat.postMessage", body)
    if result["ok"]:
        d = result["data"]
        return {"ok": True, "channel": d.get("channel"),
                "ts": d.get("ts"), "text": text}
    return result


@mcp.tool()
def send_dm(user_id: str, text: str) -> dict[str, Any]:
    """
    Send a direct message to a user.

    Args:
        user_id: Slack user ID (e.g. "U12345"). Use list_users to find IDs.
        text:    Message text.
    """
    # Open a DM channel first
    open_result = _post("conversations.open", {"users": user_id})
    if not open_result["ok"]:
        return open_result
    channel_id = open_result["data"].get("channel", {}).get("id")
    return send_message(channel_id, text)


@mcp.tool()
def list_channels(limit: int = 100, types: str = "public_channel") -> dict[str, Any]:
    """
    List channels in the workspace.

    Args:
        limit: Max channels. Default: 100.
        types: Comma-separated: "public_channel,private_channel,im,mpim"
    """
    result = _get("conversations.list",
                  {"limit": min(limit, 1000), "types": types})
    if result["ok"]:
        channels = [{"id": c["id"], "name": c.get("name"),
                     "is_private": c.get("is_private", False),
                     "member_count": c.get("num_members"),
                     "topic": c.get("topic", {}).get("value")}
                    for c in result["data"].get("channels", [])]
        return {"ok": True, "count": len(channels), "channels": channels}
    return result


@mcp.tool()
def list_users(limit: int = 100) -> dict[str, Any]:
    """List workspace users (excludes bots and deleted)."""
    result = _get("users.list", {"limit": min(limit, 1000)})
    if result["ok"]:
        users = []
        for u in result["data"].get("members", []):
            if u.get("is_bot") or u.get("deleted"):
                continue
            users.append({
                "id": u["id"], "name": u.get("name"),
                "real_name": u.get("real_name"),
                "email": u.get("profile", {}).get("email"),
                "is_admin": u.get("is_admin", False),
            })
        return {"ok": True, "count": len(users), "users": users}
    return result


@mcp.tool()
def create_channel(name: str, is_private: bool = False) -> dict[str, Any]:
    """
    Create a new channel.

    Args:
        name:       Channel name (lowercase, no spaces, max 80 chars).
        is_private: Create as private channel.
    """
    result = _post("conversations.create",
                   {"name": name.lower().replace(" ", "-"), "is_private": is_private})
    if result["ok"]:
        c = result["data"].get("channel", {})
        return {"ok": True, "channel_id": c.get("id"), "name": c.get("name"),
                "is_private": c.get("is_private")}
    return result


@mcp.tool()
def add_reaction(channel: str, timestamp: str, emoji: str) -> dict[str, Any]:
    """
    Add an emoji reaction to a message.

    Args:
        channel:   Channel ID.
        timestamp: Message timestamp (returned by send_message).
        emoji:     Emoji name without colons (e.g. "thumbsup", "tada").
    """
    result = _post("reactions.add",
                   {"channel": channel, "timestamp": timestamp,
                    "name": emoji.strip(":")})
    return {"ok": result["ok"], "channel": channel, "ts": timestamp, "emoji": emoji,
            "error": result.get("error")}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
