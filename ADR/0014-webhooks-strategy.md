# ADR-0014: Webhooks Strategy — Redis Queue, Exponential Backoff Retry

**Date:** 2026-05-24
**Status:** Accepted
**Author:** chaghadi
**Brand:** mmiri28 solutions

---

## Context

Apps need to send webhook events to external services reliably.
HTTP delivery can fail — the target server may be down, slow, or return errors.
Without retry logic, failed webhooks mean lost data for customers.

## Decision

**Delivery queue:** Redis list per endpoint — each push queues a delivery attempt.

**Retry strategy:** Exponential backoff with jitter.
- Attempt 1: immediate
- Attempt 2: 30 seconds
- Attempt 3: 5 minutes
- Attempt 4: 30 minutes
- Attempt 5: 2 hours
- After 5 failures: mark as `dead` — requires manual retry or investigation

**Signature verification:** HMAC-SHA256 of the payload with the endpoint secret.
Both outgoing (we sign) and incoming (we verify Stripe/Paystack webhooks) use the same pattern.

**Delivery log:** stored in Postgres — every attempt recorded with status, response code, duration.

**What mcp-webhooks handles:**
- Registering webhook endpoints (URL + events + secret)
- Queuing and delivering events with retry
- Verifying incoming webhook signatures (Stripe, Paystack, custom)
- Delivery log and manual retry

## Consequences

- Failed webhooks never disappear silently — always in the log
- Customers can rely on eventually-consistent webhook delivery
- Operators can inspect and manually retry any failed delivery
