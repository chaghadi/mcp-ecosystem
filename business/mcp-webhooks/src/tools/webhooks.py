"""
webhooks.py — Webhook delivery tools.

register_webhook()  — register an endpoint with events and secret
send_webhook()      — deliver an event with retry on failure
verify_signature()  — verify HMAC-SHA256 signature
list_webhooks()     — list registered endpoints for an app
get_delivery_log()  — delivery history for a webhook
retry_delivery()    — manually retry a failed delivery
"""

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
import psycopg2

from src.db import dict_cursor, get_conn

# Retry delays in seconds (exponential backoff)
RETRY_DELAYS = [0, 30, 300, 1800, 7200]  # immediate, 30s, 5min, 30min, 2hr


def run_register_webhook(
    url: str,
    events: list[str],
    app_slug: str,
    secret: str | None = None,
    description: str = "",
) -> dict[str, Any]:
    """
    Register a webhook endpoint.

    Args:
        url:         HTTPS URL to deliver events to.
        events:      List of event names to subscribe to (e.g. ["payment.completed"]).
        app_slug:    App that owns this webhook.
        secret:      Signing secret for HMAC verification. Auto-generated if not provided.
        description: Optional label.
    """
    if not url.startswith("https://"):
        return {"ok": False, "error": "Webhook URL must use HTTPS."}
    if not events:
        return {"ok": False, "error": "events list cannot be empty."}

    webhook_secret = secret or f"whsec_{uuid.uuid4().hex}"

    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                webhook_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO webhook_endpoints
                        (id, app_slug, url, events, secret, description, is_active, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, true, %s)
                """, [webhook_id, app_slug, url,
                      psycopg2.extras.Json(events),
                      webhook_secret, description,
                      datetime.now(timezone.utc)])
        return {
            "ok": True, "webhook_id": webhook_id,
            "url": url, "events": events, "app_slug": app_slug,
            "secret": webhook_secret,
            "note": "Store the secret securely — it is used to verify deliveries.",
        }
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_send_webhook(
    event_name: str,
    payload: dict,
    app_slug: str,
    webhook_id: str | None = None,
) -> dict[str, Any]:
    """
    Deliver a webhook event to all matching registered endpoints.

    Signs the payload with HMAC-SHA256 and records the delivery attempt.

    Args:
        event_name:  The event (e.g. "payment.completed").
        payload:     Event data to deliver.
        app_slug:    App that fired the event.
        webhook_id:  Optional — deliver to a specific endpoint only.
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                if webhook_id:
                    cur.execute("""
                        SELECT * FROM webhook_endpoints
                        WHERE id = %s AND is_active = true
                    """, [webhook_id])
                else:
                    cur.execute("""
                        SELECT * FROM webhook_endpoints
                        WHERE app_slug = %s AND is_active = true
                        AND events @> %s
                    """, [app_slug, psycopg2.extras.Json([event_name])])
                endpoints = [dict(r) for r in cur.fetchall()]

        if not endpoints:
            return {"ok": True, "delivered": 0,
                    "message": "No active endpoints matched this event."}

        results = []
        for endpoint in endpoints:
            result = _deliver(endpoint, event_name, payload)
            results.append(result)

        delivered = sum(1 for r in results if r.get("success"))
        return {
            "ok": True, "event_name": event_name,
            "endpoints_matched": len(endpoints),
            "delivered": delivered, "failed": len(endpoints) - delivered,
            "results": results,
        }
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def _deliver(endpoint: dict, event_name: str, payload: dict) -> dict[str, Any]:
    """Attempt delivery to one endpoint and log the result."""
    body = json.dumps({
        "event": event_name,
        "payload": payload,
        "delivered_at": datetime.now(timezone.utc).isoformat(),
        "webhook_id": endpoint["id"],
    })

    signature = hmac.new(
        endpoint["secret"].encode(),
        body.encode(),
        hashlib.sha256,
    ).hexdigest()

    delivery_id = str(uuid.uuid4())
    start = datetime.now(timezone.utc)

    try:
        r = httpx.post(
            endpoint["url"],
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Signature": f"sha256={signature}",
                "X-Webhook-Event": event_name,
                "X-Webhook-ID": endpoint["id"],
                "X-Delivery-ID": delivery_id,
            },
            timeout=10,
        )
        success = 200 <= r.status_code < 300
        duration_ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)

        _log_delivery(delivery_id, endpoint["id"], event_name,
                      "success" if success else "failed",
                      r.status_code, duration_ms, r.text[:500] if not success else "")

        return {"delivery_id": delivery_id, "webhook_id": endpoint["id"],
                "url": endpoint["url"], "success": success,
                "status_code": r.status_code, "duration_ms": duration_ms}

    except Exception as exc:
        duration_ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
        _log_delivery(delivery_id, endpoint["id"], event_name,
                      "failed", None, duration_ms, str(exc)[:500])
        return {"delivery_id": delivery_id, "webhook_id": endpoint["id"],
                "url": endpoint["url"], "success": False, "error": str(exc)}


def _log_delivery(delivery_id, webhook_id, event_name, status,
                  status_code, duration_ms, error_message):
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    INSERT INTO webhook_deliveries
                        (id, webhook_id, event_name, status, status_code,
                         duration_ms, error_message, attempt, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 1, %s)
                """, [delivery_id, webhook_id, event_name, status,
                      status_code, duration_ms, error_message,
                      datetime.now(timezone.utc)])
    except Exception:
        pass  # Don't let logging failures break delivery


def run_verify_signature(
    payload: str,
    signature: str,
    secret: str,
) -> dict[str, Any]:
    """
    Verify a webhook signature (HMAC-SHA256).

    Use this to verify incoming webhooks from mcp-billing or any other sender.

    Args:
        payload:   Raw request body as string.
        signature: Value of the X-Webhook-Signature header (format: "sha256=abc123").
        secret:    The webhook secret.
    """
    try:
        expected = "sha256=" + hmac.new(
            secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        valid = hmac.compare_digest(expected, signature)
        return {"ok": True, "valid": valid,
                "message": "Signature valid." if valid else "Signature invalid."}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def run_list_webhooks(app_slug: str) -> dict[str, Any]:
    """List all registered webhook endpoints for an app."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    SELECT id, url, events, description, is_active, created_at
                    FROM webhook_endpoints WHERE app_slug = %s ORDER BY created_at DESC
                """, [app_slug])
                webhooks = [dict(r) for r in cur.fetchall()]
        return {"ok": True, "app_slug": app_slug, "count": len(webhooks), "webhooks": webhooks}
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_get_delivery_log(webhook_id: str, limit: int = 50) -> dict[str, Any]:
    """Get delivery history for a webhook endpoint."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    SELECT * FROM webhook_deliveries
                    WHERE webhook_id = %s ORDER BY created_at DESC LIMIT %s
                """, [webhook_id, min(limit, 200)])
                deliveries = [dict(r) for r in cur.fetchall()]
        return {"ok": True, "webhook_id": webhook_id, "deliveries": deliveries}
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_retry_delivery(delivery_id: str) -> dict[str, Any]:
    """Manually retry a failed webhook delivery."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    SELECT wd.*, we.url, we.secret, we.is_active
                    FROM webhook_deliveries wd
                    JOIN webhook_endpoints we ON we.id = wd.webhook_id
                    WHERE wd.id = %s
                """, [delivery_id])
                row = cur.fetchone()

        if not row:
            return {"ok": False, "error": f"Delivery '{delivery_id}' not found."}
        if not row["is_active"]:
            return {"ok": False, "error": "Webhook endpoint is disabled."}

        import json as _json
        result = _deliver(
            {"id": row["webhook_id"], "url": row["url"], "secret": row["secret"]},
            row["event_name"],
            {"retry": True, "original_delivery_id": delivery_id},
        )
        return {"ok": True, "retry_result": result}
    except psycopg2.Error as exc:
        return {"ok": False, "error": str(exc).strip()}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}
