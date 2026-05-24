"""server.py — mcp-billing MCP server entry point."""

import subprocess
from typing import Any
from mcp.server.fastmcp import FastMCP
from src.config import settings
from src.tools import stripe_provider as _stripe
from src.tools import paystack_provider as _paystack

mcp = FastMCP(
    "mcp-billing",
    instructions=(
        "Billing MCP for mmiri28 solutions. "
        "Stripe for international payments. Paystack for Nigeria/Africa (NGN). "
        "Currency auto-routes to the correct provider. "
        "Supports one-time payments and subscriptions."
    ),
)


def _provider(currency: str | None, explicit: str | None):
    return settings.provider_for(currency, explicit)


def _dispatch(provider: str, fn_stripe, fn_paystack, *args, **kwargs) -> dict:
    if provider == "paystack":
        return fn_paystack(*args, **kwargs)
    return fn_stripe(*args, **kwargs)


@mcp.tool()
def health_check() -> dict:
    """Check connectivity to Stripe and Paystack."""
    results = {}
    stripe_err = settings.validate_stripe()
    results["stripe"] = "configured" if not stripe_err else f"not configured: {stripe_err}"
    paystack_err = settings.validate_paystack()
    results["paystack"] = "configured" if not paystack_err else f"not configured: {paystack_err}"
    results["default_currency"] = settings.default_currency
    results["default_provider"] = settings.provider_for()
    return {"ok": True, "providers": results}


@mcp.tool()
def run_migrations() -> dict:
    """Run pending Alembic migrations for billing tables."""
    if not settings.database_url:
        return {"ok": False, "error": "DATABASE_URL not set."}
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        capture_output=True, text=True, cwd=str(settings.mcp_root),
    )
    if result.returncode != 0:
        return {"ok": False, "error": result.stderr or result.stdout}
    return {"ok": True, "output": result.stdout or "Migrations applied."}


@mcp.tool()
def create_customer(
    email: str, name: str, user_id: str,
    currency: str | None = None,
    provider: str | None = None,
    phone: str = "",
) -> dict:
    """
    Create a billing customer in Stripe or Paystack.

    Args:
        email:    Customer email.
        name:     Full name.
        user_id:  UUID from mcp-auth.
        currency: Determines provider. NGN → Paystack, others → Stripe.
        provider: Override auto-detection: "stripe" or "paystack".
        phone:    Phone number (used by Paystack).
    """
    p = _provider(currency, provider)
    if p == "paystack":
        return _paystack.create_customer(email, name, user_id, phone)
    return _stripe.create_customer(email, name, user_id)


@mcp.tool()
def get_customer(customer_id: str, provider: str = "stripe") -> dict:
    """Get a billing customer by their provider ID."""
    return _dispatch(provider, _stripe.get_customer, _paystack.get_customer, customer_id)


@mcp.tool()
def create_payment_intent(
    amount: int,
    currency: str,
    customer_id: str | None = None,
    description: str = "",
    metadata: dict | None = None,
    provider: str | None = None,
    callback_url: str = "",
) -> dict:
    """
    Create a payment for a one-time charge.

    Amount must be in smallest denomination:
      USD/EUR/GBP: cents  (100 = $1.00)
      NGN: kobo           (10000 = ₦100)
      GHS: pesewas

    Stripe returns a client_secret for frontend SDK.
    Paystack returns an authorization_url — redirect user there.

    Args:
        amount:       Amount in smallest denomination.
        currency:     ISO currency code (USD, NGN, EUR, GBP, GHS...).
        customer_id:  Provider customer ID (optional).
        description:  Payment description.
        metadata:     Extra key-value data.
        provider:     Override auto-routing.
        callback_url: Paystack only — redirect URL after payment.
    """
    p = _provider(currency, provider)
    meta = metadata or {}
    if p == "paystack":
        return _paystack.create_payment_intent(amount, currency, customer_id, description, meta, callback_url)
    return _stripe.create_payment_intent(amount, currency, customer_id, description, meta)


@mcp.tool()
def get_payment(payment_id: str, provider: str = "stripe") -> dict:
    """Get a payment/transaction by its provider ID or reference."""
    return _dispatch(provider,
                     _stripe.get_payment_intent,
                     _paystack.get_payment_intent,
                     payment_id)


@mcp.tool()
def create_plan(
    name: str,
    amount: int,
    currency: str,
    interval: str = "month",
    provider: str | None = None,
) -> dict:
    """
    Create a subscription plan/price.

    Args:
        name:     Plan name (e.g. "Pro Monthly").
        amount:   Amount in smallest denomination.
        currency: ISO currency code.
        interval: "month" or "year" (Stripe) / "monthly" or "annually" (Paystack).
        provider: Override auto-routing.
    """
    p = _provider(currency, provider)
    # Normalize interval for each provider
    if p == "paystack":
        ps_interval = "annually" if "year" in interval else "monthly"
        return _paystack.create_plan(name, amount, currency, ps_interval)
    return _stripe.create_plan(name, amount, currency, interval)


@mcp.tool()
def create_subscription(
    customer_id: str,
    plan_id: str,
    trial_days: int = 0,
    provider: str = "stripe",
) -> dict:
    """
    Subscribe a customer to a plan.

    Args:
        customer_id: Provider customer ID.
        plan_id:     Provider plan/price ID.
        trial_days:  Free trial days before billing starts.
        provider:    "stripe" or "paystack".
    """
    return _dispatch(provider,
                     lambda c, p, t: _stripe.create_subscription(c, p, t),
                     lambda c, p, t: _paystack.create_subscription(c, p, t),
                     customer_id, plan_id, trial_days)


@mcp.tool()
def cancel_subscription(
    subscription_id: str,
    immediately: bool = False,
    provider: str = "stripe",
) -> dict:
    """
    Cancel a subscription.

    Args:
        subscription_id: Provider subscription ID.
        immediately:     True = cancel now. False = cancel at period end.
        provider:        "stripe" or "paystack".
    """
    return _dispatch(provider,
                     lambda s, i: _stripe.cancel_subscription(s, i),
                     lambda s, i: _paystack.cancel_subscription(s, i),
                     subscription_id, immediately)


@mcp.tool()
def get_subscription(subscription_id: str, provider: str = "stripe") -> dict:
    """Get a subscription by its provider ID."""
    return _dispatch(provider,
                     _stripe.get_subscription,
                     _paystack.get_subscription,
                     subscription_id)


@mcp.tool()
def create_portal_session(
    customer_id: str,
    return_url: str,
    provider: str = "stripe",
) -> dict:
    """
    Create a billing portal session (Stripe only).
    Returns a URL the customer visits to manage their subscription.
    """
    if provider != "stripe":
        return {"ok": False, "error": "Billing portal is only available for Stripe."}
    return _stripe.create_portal_session(customer_id, return_url)


@mcp.tool()
def verify_webhook(
    payload: str,
    signature: str,
    provider: str = "stripe",
) -> dict:
    """
    Verify and parse an incoming webhook from Stripe or Paystack.

    Args:
        payload:   Raw request body as string.
        signature: Signature header value.
        provider:  "stripe" or "paystack".
    """
    return _dispatch(provider,
                     _stripe.verify_webhook,
                     _paystack.verify_webhook,
                     payload, signature)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
