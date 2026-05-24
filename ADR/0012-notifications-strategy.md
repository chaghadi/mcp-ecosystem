# ADR-0012: Notifications Strategy — Resend + Twilio + Termii

**Date:** 2026-05-24
**Status:** Accepted
**Author:** chaghadi
**Brand:** mmiri28 solutions

---

## Context

Apps need email, SMS, and push notifications. Nigerian users have specific
requirements: local SMS providers are cheaper and more reliable than
international ones for Nigerian phone numbers.

## Decision

**Email:** Resend — modern API, generous free tier (3000/month), excellent deliverability.

**SMS international:** Twilio — global standard, reliable.

**SMS Nigeria:** Termii — Nigerian provider, cheaper for NG numbers, supports
local sender IDs, USSD, and WhatsApp. Used when `to` number starts with `+234`.

**Push:** Stub — implemented when an app needs it (FCM or APNs).

**Auto-routing for SMS:**
- `+234*` (Nigeria) → Termii
- Everything else → Twilio
- Override with explicit `provider` param

## Consequences

- Nigerian SMS costs significantly less than Twilio rates for NG numbers
- Developers don't need to know which SMS provider is used
- Adding WhatsApp notifications = already supported via Termii's API
