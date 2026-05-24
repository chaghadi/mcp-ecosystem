# ADR-0007: Storage Strategy — Cloudflare R2

**Date:** 2026-05-24
**Status:** Accepted
**Author:** chaghadi
**Brand:** mmiri28 solutions

---

## Context

Apps need to store and serve files — user uploads, product images, documents,
exports. We needed a storage provider that is:
- Free or near-free while building
- Zero egress cost at scale (serving files to users should not have a per-GB fee)
- S3-compatible (portable, no vendor SDK lock-in)
- Supports both private files (user docs) and public files (product assets)

## Decision

**Cloudflare R2** for all file storage.

**Why R2 over alternatives:**
- Zero egress fees — serving 1TB of files costs the same as serving 1MB
- S3-compatible API — `boto3` works unchanged; migrating to any S3-compatible
  provider is a one-line endpoint change
- 10GB free storage + 1M Class A operations/month free forever
- Supports both private buckets (signed URLs) and public buckets (stable URLs)

**Two bucket types:**

| Type | Access | Use case |
|------|--------|----------|
| Private | Signed URLs (time-limited) | User uploads, documents, invoices |
| Public | Stable URL via custom domain | Logos, product images, public assets |

**Credentials:** `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`
**Public domain:** `R2_PUBLIC_DOMAIN` — set to your R2.dev subdomain or custom domain

**Migration path:**
Swap `R2_ACCOUNT_ID` and credentials → any S3-compatible provider.
No code changes required.

## Consequences

- No egress costs ever — file serving is free regardless of traffic
- Private files are never directly accessible — always through signed URLs
- Public files have stable, cacheable URLs served via Cloudflare's CDN
- `boto3` is the only dependency — no Cloudflare-specific SDK
