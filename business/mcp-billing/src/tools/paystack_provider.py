"""
paystack_provider.py — Paystack API wrapper for mcp-billing.

Handles customers, transactions (one-time), and subscriptions
for Nigerian and West African markets.

All amounts in Paystack are in the smallest denomination:
  NGN: kobo (₦100 = 10000 kobo)
  GHS: pesewas
  ZAR: cents

Paystack API base: https://api.paystack.co
"""

import httpx
from typing import Any
from src.config import settings

BASE = "https://api.paystack.co"


def _headers() -> dict[str, str]:
    error = settings.validate_paystack()
    if error:
        raise RuntimeError(error)
    return {
        "Authorization": f"Bearer {settings.paystack_secret_key}",
        "Content-Type": "application/json",
    }


def _get(path: str) -> dict[str, Any]:
    try:
        r = httpx.get(f"{BASE}{path}", headers=_headers(), timeout=10)
        data = r.json()
        return {"ok": data.get("status", False), "data": data.get("data"), "message": data.get("message", "")}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _post(path: str, body: dict) -> dict[str, Any]:
    try:
        r = httpx.post(f"{BASE}{path}", headers=_headers(), json=body, timeout=10)
        data = r.json()
        return {"ok": data.get("status", False), "data": data.get("data"), "message": data.get("message", "")}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


# ── Customers ─────────────────────────────────────────────────────────────────

def create_customer(email: str, name: str, user_id: str, phone: str = "", metadata: dict = {}) -> dict[str, Any]:
    result = _post("/customer", {
        "email": email, "first_name": name.split()[0] if name else "",
        "last_name": " ".join(name.split()[1:]) if len(name.split()) > 1 else "",
        "phone": phone, "metadata": {"user_id": user_id, **metadata},
    })
    if result["ok"] and result["data"]:
        return {
            "ok": True, "provider": "paystack",
            "customer_id": result["data"]["customer_code"],
            "email": result["data"]["email"],
        }
    return {"ok": False, "provider": "paystack", "error": result.get("message", "Unknown error")}


def get_customer(customer_code: str) -> dict[str, Any]:
    result = _get(f"/customer/{customer_code}")
    if result["ok"]:
        return {"ok": True, "provider": "paystack", "customer": result["data"]}
    return {"ok": False, "error": result.get("message", "Unknown error")}


# ── One-time payments ─────────────────────────────────────────────────────────

def create_payment_intent(
    amount: int, currency: str, customer_id: str | None = None,
    description: str = "", metadata: dict = {}, callback_url: str = ""
) -> dict[str, Any]:
    """
    Initialize a Paystack transaction.
    Returns authorization_url — redirect user here to complete payment.
    amount must be in kobo (NGN) or pesewas (GHS).
    """
    body: dict = {
        "amount": amount,
        "currency": currency.upper(),
        "metadata": {"description": description, **metadata},
    }
    if customer_id:
        body["customer"] = customer_id
    if callback_url:
        body["callback_url"] = callback_url

    result = _post("/transaction/initialize", body)
    if result["ok"] and result["data"]:
        return {
            "ok": True, "provider": "paystack",
            "payment_intent_id": result["data"]["reference"],
            "authorization_url": result["data"]["authorization_url"],
            "access_code": result["data"]["access_code"],
            "amount": amount, "currency": currency,
            "status": "pending",
        }
    return {"ok": False, "error": result.get("message", "Unknown error")}


def get_payment_intent(reference: str) -> dict[str, Any]:
    """Verify a Paystack transaction by reference."""
    result = _get(f"/transaction/verify/{reference}")
    if result["ok"]:
        return {"ok": True, "provider": "paystack", "payment_intent": result["data"]}
    return {"ok": False, "error": result.get("message", "Unknown error")}


# ── Plans & Subscriptions ─────────────────────────────────────────────────────

def create_plan(
    name: str, amount: int, currency: str,
    interval: str = "monthly", interval_count: int = 1,
    metadata: dict = {}
) -> dict[str, Any]:
    """
    interval: "hourly"|"daily"|"weekly"|"monthly"|"annually"
    """
    result = _post("/plan", {
        "name": name, "amount": amount,
        "interval": interval, "currency": currency.upper(),
    })
    if result["ok"] and result["data"]:
        return {
            "ok": True, "provider": "paystack",
            "plan_id": result["data"]["plan_code"],
            "name": name, "amount": amount, "currency": currency,
            "interval": interval,
        }
    return {"ok": False, "error": result.get("message", "Unknown error")}


def create_subscription(
    customer_id: str, plan_id: str,
    trial_days: int = 0, metadata: dict = {}
) -> dict[str, Any]:
    body: dict = {"customer": customer_id, "plan": plan_id}
    if trial_days > 0:
        from datetime import datetime, timedelta, timezone
        start = datetime.now(timezone.utc) + timedelta(days=trial_days)
        body["start_date"] = start.strftime("%Y-%m-%dT%H:%M:%S+00:00")

    result = _post("/subscription", body)
    if result["ok"] and result["data"]:
        return {
            "ok": True, "provider": "paystack",
            "subscription_id": result["data"]["subscription_code"],
            "status": result["data"]["status"],
        }
    return {"ok": False, "error": result.get("message", "Unknown error")}


def cancel_subscription(subscription_id: str, immediately: bool = False) -> dict[str, Any]:
    result = _post("/subscription/disable", {
        "code": subscription_id, "token": subscription_id
    })
    return {
        "ok": result["ok"], "provider": "paystack",
        "subscription_id": subscription_id,
        "message": result.get("message", ""),
    }


def get_subscription(subscription_id: str) -> dict[str, Any]:
    result = _get(f"/subscription/{subscription_id}")
    if result["ok"]:
        return {"ok": True, "provider": "paystack", "subscription": result["data"]}
    return {"ok": False, "error": result.get("message", "Unknown error")}


def verify_webhook(payload: str, sig_header: str) -> dict[str, Any]:
    """Verify an incoming Paystack webhook using HMAC-SHA512."""
    import hashlib, hmac
    if not settings.paystack_secret_key:
        return {"ok": False, "error": "PAYSTACK_SECRET_KEY not set."}
    try:
        expected = hmac.new(
            settings.paystack_secret_key.encode(),
            payload.encode(), hashlib.sha512
        ).hexdigest()
        if not hmac.compare_digest(expected, sig_header):
            return {"ok": False, "error": "Invalid Paystack webhook signature."}
        import json
        event = json.loads(payload)
        return {"ok": True, "provider": "paystack",
                "event_type": event.get("event"), "event": event}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
