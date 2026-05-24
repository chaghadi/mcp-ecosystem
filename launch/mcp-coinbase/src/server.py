"""server.py — mcp-coinbase MCP server entry point.

Coinbase Commerce — accept BTC, ETH, USDC and other cryptocurrencies.
Create charges (payment requests), check status, verify webhooks.
"""

import hashlib
import hmac
import httpx
from typing import Any
from mcp.server.fastmcp import FastMCP
from src.config import settings

mcp = FastMCP(
    "mcp-coinbase",
    instructions="Coinbase Commerce MCP for mmiri28 solutions. Accept crypto payments — BTC, ETH, USDC, and more. Create charges, check status, verify webhooks.",
)


def _get(path: str) -> dict[str, Any]:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        r = httpx.get(f"{settings.base_url}{path}", headers=settings.headers, timeout=15)
        data = r.json()
        if r.status_code == 200:
            return {"ok": True, "data": data.get("data")}
        return {"ok": False, "error": data.get("error", {}).get("message", f"HTTP {r.status_code}")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _post(path: str, body: dict) -> dict[str, Any]:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        r = httpx.post(f"{settings.base_url}{path}", headers=settings.headers, json=body, timeout=15)
        data = r.json()
        if r.status_code in (200, 201):
            return {"ok": True, "data": data.get("data")}
        return {"ok": False, "error": data.get("error", {}).get("message", f"HTTP {r.status_code}")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def health_check() -> dict:
    """Verify Coinbase Commerce API key."""
    result = _get("/checkouts?limit=1")
    if result["ok"]:
        return {"ok": True, "status": "connected"}
    return result


@mcp.tool()
def create_charge(
    name: str, description: str, amount: float, currency: str = "USD",
    redirect_url: str | None = None, cancel_url: str | None = None,
    metadata: dict | None = None,
) -> dict[str, Any]:
    """
    Create a crypto payment charge.

    The customer pays in BTC, ETH, USDC, DAI, or other supported crypto.
    The amount is quoted in fiat (USD/EUR) but paid in crypto at the current rate.

    Args:
        name:         Product/service name shown to customer.
        description:  Description of what they're paying for.
        amount:       Amount in fiat (e.g. 9.99 for $9.99).
        currency:     Fiat currency code (USD, EUR, etc.). Default: USD.
        redirect_url: Where to send customer after successful payment.
        cancel_url:   Where to send customer if they cancel.
        metadata:     Custom key/value data (e.g. {"user_id": "...", "order_id": "..."}).
    """
    body: dict = {
        "name": name, "description": description,
        "pricing_type": "fixed_price",
        "local_price": {"amount": f"{amount:.2f}", "currency": currency.upper()},
        "metadata": metadata or {},
    }
    if redirect_url: body["redirect_url"] = redirect_url
    if cancel_url:   body["cancel_url"] = cancel_url

    result = _post("/charges", body)
    if result["ok"]:
        d = result["data"]
        return {
            "ok": True, "charge_id": d["id"], "code": d["code"],
            "hosted_url": d["hosted_url"],
            "amount": amount, "currency": currency.upper(),
            "expires_at": d.get("expires_at"),
        }
    return result


@mcp.tool()
def get_charge(charge_id_or_code: str) -> dict[str, Any]:
    """
    Get charge status by ID or short code.

    Status values: NEW, PENDING, COMPLETED, EXPIRED, UNRESOLVED, RESOLVED, CANCELED.
    """
    result = _get(f"/charges/{charge_id_or_code}")
    if result["ok"]:
        d = result["data"]
        timeline = d.get("timeline", [])
        latest_status = timeline[-1]["status"] if timeline else "UNKNOWN"
        return {
            "ok": True, "charge_id": d["id"], "code": d["code"],
            "status": latest_status, "name": d.get("name"),
            "pricing": d.get("pricing"),
            "payments": d.get("payments", []),
            "expires_at": d.get("expires_at"),
            "hosted_url": d.get("hosted_url"),
        }
    return result


@mcp.tool()
def list_charges(limit: int = 25) -> dict[str, Any]:
    """List recent charges."""
    result = _get(f"/charges?limit={min(limit, 100)}")
    if result["ok"]:
        charges = []
        for c in result["data"]:
            timeline = c.get("timeline", [])
            status = timeline[-1]["status"] if timeline else "UNKNOWN"
            charges.append({
                "id": c["id"], "code": c["code"], "name": c.get("name"),
                "status": status,
                "amount": c.get("pricing", {}).get("local", {}).get("amount"),
                "currency": c.get("pricing", {}).get("local", {}).get("currency"),
                "created_at": c.get("created_at"),
            })
        return {"ok": True, "count": len(charges), "charges": charges}
    return result


@mcp.tool()
def verify_webhook(payload: str, signature: str) -> dict[str, Any]:
    """
    Verify a Coinbase Commerce webhook signature.

    Args:
        payload:   Raw request body as string.
        signature: Value of the X-CC-Webhook-Signature header.
    """
    if not settings.webhook_secret or "your-" in settings.webhook_secret:
        return {"ok": False, "error": "COINBASE_WEBHOOK_SECRET not configured."}

    try:
        expected = hmac.new(
            settings.webhook_secret.encode(),
            payload.encode(), hashlib.sha256
        ).hexdigest()
        valid = hmac.compare_digest(expected, signature)
        return {
            "ok": True, "valid": valid,
            "message": "Webhook signature valid." if valid else "Invalid signature.",
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
