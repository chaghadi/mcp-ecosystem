"""
stripe_provider.py — Stripe API wrapper for mcp-billing.

Handles customers, one-time payments (PaymentIntent),
subscriptions, and plans for international currencies.
"""

from typing import Any
import stripe as stripe_lib
from src.config import settings


def _client():
    error = settings.validate_stripe()
    if error:
        raise RuntimeError(error)
    stripe_lib.api_key = settings.stripe_secret_key
    return stripe_lib


# ── Customers ─────────────────────────────────────────────────────────────────

def create_customer(email: str, name: str, user_id: str, metadata: dict = {}) -> dict[str, Any]:
    try:
        s = _client()
        customer = s.Customer.create(
            email=email, name=name,
            metadata={"user_id": user_id, **metadata}
        )
        return {"ok": True, "provider": "stripe", "customer_id": customer.id,
                "email": customer.email}
    except stripe_lib.StripeError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def get_customer(customer_id: str) -> dict[str, Any]:
    try:
        s = _client()
        c = s.Customer.retrieve(customer_id)
        return {"ok": True, "provider": "stripe", "customer": c.to_dict()}
    except stripe_lib.StripeError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


# ── One-time payments ─────────────────────────────────────────────────────────

def create_payment_intent(
    amount: int, currency: str, customer_id: str | None = None,
    description: str = "", metadata: dict = {}
) -> dict[str, Any]:
    try:
        s = _client()
        params = {
            "amount": amount, "currency": currency.lower(),
            "description": description, "metadata": metadata,
            "automatic_payment_methods": {"enabled": True},
        }
        if customer_id:
            params["customer"] = customer_id
        pi = s.PaymentIntent.create(**params)
        return {
            "ok": True, "provider": "stripe",
            "payment_intent_id": pi.id,
            "client_secret": pi.client_secret,
            "amount": amount, "currency": currency,
            "status": pi.status,
        }
    except stripe_lib.StripeError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def get_payment_intent(payment_intent_id: str) -> dict[str, Any]:
    try:
        s = _client()
        pi = s.PaymentIntent.retrieve(payment_intent_id)
        return {"ok": True, "provider": "stripe", "payment_intent": pi.to_dict()}
    except stripe_lib.StripeError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


# ── Plans & Subscriptions ─────────────────────────────────────────────────────

def create_plan(
    name: str, amount: int, currency: str,
    interval: str = "month", interval_count: int = 1,
    metadata: dict = {}
) -> dict[str, Any]:
    try:
        s = _client()
        product = s.Product.create(name=name)
        price = s.Price.create(
            product=product.id, unit_amount=amount,
            currency=currency.lower(),
            recurring={"interval": interval, "interval_count": interval_count},
            metadata=metadata,
        )
        return {
            "ok": True, "provider": "stripe",
            "plan_id": price.id, "product_id": product.id,
            "name": name, "amount": amount, "currency": currency,
            "interval": interval,
        }
    except stripe_lib.StripeError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def create_subscription(
    customer_id: str, plan_id: str, trial_days: int = 0,
    metadata: dict = {}
) -> dict[str, Any]:
    try:
        s = _client()
        params: dict = {
            "customer": customer_id,
            "items": [{"price": plan_id}],
            "metadata": metadata,
        }
        if trial_days > 0:
            params["trial_period_days"] = trial_days
        sub = s.Subscription.create(**params)
        return {
            "ok": True, "provider": "stripe",
            "subscription_id": sub.id,
            "status": sub.status,
            "current_period_end": sub.current_period_end,
        }
    except stripe_lib.StripeError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def cancel_subscription(subscription_id: str, immediately: bool = False) -> dict[str, Any]:
    try:
        s = _client()
        if immediately:
            sub = s.Subscription.cancel(subscription_id)
        else:
            sub = s.Subscription.modify(subscription_id, cancel_at_period_end=True)
        return {
            "ok": True, "provider": "stripe",
            "subscription_id": subscription_id,
            "status": sub.status,
            "cancel_at_period_end": sub.cancel_at_period_end,
        }
    except stripe_lib.StripeError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def get_subscription(subscription_id: str) -> dict[str, Any]:
    try:
        s = _client()
        sub = s.Subscription.retrieve(subscription_id)
        return {"ok": True, "provider": "stripe", "subscription": sub.to_dict()}
    except stripe_lib.StripeError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def create_portal_session(customer_id: str, return_url: str) -> dict[str, Any]:
    """Stripe billing portal — let customers manage their own subscriptions."""
    try:
        s = _client()
        session = s.billing_portal.Session.create(
            customer=customer_id, return_url=return_url
        )
        return {"ok": True, "provider": "stripe", "url": session.url}
    except stripe_lib.StripeError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def verify_webhook(payload: str, sig_header: str) -> dict[str, Any]:
    """Verify and parse an incoming Stripe webhook."""
    try:
        s = _client()
        if not settings.stripe_webhook_secret:
            return {"ok": False, "error": "STRIPE_WEBHOOK_SECRET not set."}
        event = s.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
        return {"ok": True, "provider": "stripe",
                "event_type": event.type, "event": event.to_dict()}
    except stripe_lib.SignatureVerificationError:
        return {"ok": False, "error": "Invalid Stripe webhook signature."}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
