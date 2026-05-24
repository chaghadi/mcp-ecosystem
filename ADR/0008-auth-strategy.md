# ADR-0008: Authentication Strategy

**Date:** 2026-05-24
**Status:** Accepted
**Author:** chaghadi
**Brand:** mmiri28 solutions

---

## Context

mmiri28 builds multiple apps under one brand. Each app may have different
login methods and different role structures. We needed an auth system that:
- Supports email, phone, and username login from day one
- Adds Google OAuth later without restructuring
- Handles roles that differ per app (a seller in the marketplace is not
  a developer in the SaaS tool)
- Has one global superadmin role for cross-app operations

## Decision

**Auth methods:** email+password, phone+password, username+password.
Google OAuth registered as a stub — same interface, not yet implemented.

**Token strategy:**
- Access token: JWT, 15-minute TTL, signed with `JWT_SECRET`
- Refresh token: random UUID, hashed before storage in `refresh_tokens` table,
  30-day TTL. Stored in Postgres, revocable.
- Blacklist: revoked access tokens stored in Redis until their natural expiry.
  Keeps logout instant without waiting for token expiry.

**Role model — Option C (global + app-scoped):**
- `users.global_role`: `superadmin` | `user`. One value per user, cross-app.
- `app_roles` table: role definitions owned by each app slug.
- `user_app_roles` table: user ↔ app ↔ role assignments.
- A user can be `seller` in `marketplace` and `owner` in `saas-tool` simultaneously.
- Superadmin bypasses all app-level role checks.

**Schema tables:** `users`, `apps`, `app_roles`, `user_app_roles`,
`oauth_accounts` (for future OAuth), `refresh_tokens`.

## Consequences

- Adding Google OAuth = implement the two OAuth stubs + add rows to `oauth_accounts`
- Adding a new auth method = add a column to `users` + one migration
- Role changes never require auth schema changes — just data changes
- Any app can call `verify_token(access_token, app_slug)` and get back
  the user's identity + their roles in that app in one call
