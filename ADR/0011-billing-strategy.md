# ADR-0011: Billing Strategy — Stripe + Paystack, Provider Pattern

**Date:** 2026-05-24
**Status:** Accepted
**Author:** chaghadi
**Brand:** mmiri28 solutions

---

## Context

mmiri28 builds apps for international markets and the Nigerian market.
Stripe is the global standard but has limited reach in Nigeria.
Paystack dominates Nigeria and is owned by Stripe but has a different API.
We needed one billing MCP that handles both without apps knowing the difference.

## Decision

**Provider pattern:** currency determines the provider automatically.
- `NGN` → Paystack
- Everything else → Stripe

Apps call the same tools regardless of provider.
The `provider` param can override auto-detection when needed.

**Both providers support:**
- One-time payments (Stripe: PaymentIntent / Paystack: Transaction)
- Subscriptions (Stripe: Subscription / Paystack: Subscription)
- Customers
- Webhooks

**Amount convention:** always pass amounts in the **smallest denomination**:
- USD: cents (100 = $1.00)
- NGN: kobo (10000 = ₦100)

**Supported currencies:** USD, EUR, GBP, NGN, GHS, KES, ZAR (Paystack covers West/East Africa)

## Consequences

- Nigerian apps use Paystack automatically — no extra config
- International apps use Stripe automatically
- Adding a new provider = implement its adapter in `src/providers/`
- Webhooks from both providers verified and normalized in `mcp-webhooks`
