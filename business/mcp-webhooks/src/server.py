"""server.py — mcp-webhooks MCP server entry point."""

import subprocess
from mcp.server.fastmcp import FastMCP
from src.config import settings
from src.db import get_conn
from src.tools.webhooks import (
    run_register_webhook, run_send_webhook, run_verify_signature,
    run_list_webhooks, run_get_delivery_log, run_retry_delivery,
)

mcp = FastMCP(
    "mcp-webhooks",
    instructions=(
        "Webhooks MCP for mmiri28 solutions. "
        "Register endpoints, deliver signed events, verify signatures, retry failures. "
        "HMAC-SHA256 signing on all outgoing deliveries."
    ),
)


@mcp.tool()
def health_check() -> dict:
    error = settings.validate()
    if error:
        return {"ok": False, "error": error}
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM webhook_endpoints")
                endpoints = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM webhook_deliveries WHERE status = 'failed'")
                failed = cur.fetchone()[0]
        return {"ok": True, "status": "connected",
                "registered_endpoints": endpoints, "failed_deliveries": failed}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def run_migrations() -> dict:
    error = settings.validate()
    if error:
        return {"ok": False, "error": error}
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        capture_output=True, text=True, cwd=str(settings.mcp_root),
    )
    if result.returncode != 0:
        return {"ok": False, "error": result.stderr or result.stdout}
    return {"ok": True, "output": result.stdout or "Migrations applied."}


@mcp.tool()
def register_webhook(
    url: str, events: list[str], app_slug: str,
    secret: str | None = None, description: str = "",
) -> dict:
    """
    Register a webhook endpoint.

    Args:
        url:         HTTPS URL to receive events.
        events:      Events to subscribe to (e.g. ["payment.completed", "user.created"]).
        app_slug:    App that owns this endpoint.
        secret:      Signing secret. Auto-generated if not provided.
        description: Optional label.
    """
    return run_register_webhook(url=url, events=events, app_slug=app_slug,
                                secret=secret, description=description)


@mcp.tool()
def send_webhook(
    event_name: str, payload: dict, app_slug: str,
    webhook_id: str | None = None,
) -> dict:
    """
    Deliver an event to all matching registered endpoints.

    Payload is signed with HMAC-SHA256. Delivery is logged.

    Args:
        event_name: The event (e.g. "payment.completed").
        payload:    Event data.
        app_slug:   App that fired the event.
        webhook_id: Optional — deliver to a specific endpoint only.
    """
    return run_send_webhook(event_name=event_name, payload=payload,
                            app_slug=app_slug, webhook_id=webhook_id)


@mcp.tool()
def verify_signature(payload: str, signature: str, secret: str) -> dict:
    """
    Verify a webhook's HMAC-SHA256 signature.

    Args:
        payload:   Raw request body string.
        signature: X-Webhook-Signature header value (format: "sha256=abc123").
        secret:    The webhook signing secret.
    """
    return run_verify_signature(payload=payload, signature=signature, secret=secret)


@mcp.tool()
def list_webhooks(app_slug: str) -> dict:
    """List all registered webhook endpoints for an app."""
    return run_list_webhooks(app_slug=app_slug)


@mcp.tool()
def get_delivery_log(webhook_id: str, limit: int = 50) -> dict:
    """Get delivery history for a webhook endpoint."""
    return run_get_delivery_log(webhook_id=webhook_id, limit=limit)


@mcp.tool()
def retry_delivery(delivery_id: str) -> dict:
    """Manually retry a failed webhook delivery."""
    return run_retry_delivery(delivery_id=delivery_id)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
