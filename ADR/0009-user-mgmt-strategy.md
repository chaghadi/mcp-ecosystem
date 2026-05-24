# ADR-0009: User Management Strategy

**Date:** 2026-05-24
**Status:** Accepted
**Author:** chaghadi
**Brand:** mmiri28 solutions

---

## Context

`mcp-auth` owns identity and access — who you are and what you can do.
`mcp-user-mgmt` owns everything about a user as a person:
their profile, preferences, and full account lifecycle.

We needed a clear boundary so the two MCPs stay focused and don't duplicate.

## Decision

**Boundary:**
- `mcp-auth` → authentication, tokens, roles
- `mcp-user-mgmt` → profiles, preferences, lifecycle (GDPR delete, data export)

**Preferences model — flexible JSONB (Option B):**
Preferences are stored in a single JSONB column, namespaced by app slug:
```json
{
  "global":      { "timezone": "Europe/Vienna", "language": "en" },
  "marketplace": { "theme": "dark", "email_notifications": true },
  "saas-tool":   { "sidebar_collapsed": false }
}
```
- No schema migration needed to add a new preference key
- Each app reads and writes only its own namespace
- `global` namespace for cross-app preferences
- Querying a specific app's preferences is a single JSONB path lookup

**Lifecycle:**
- Soft delete: handled by `mcp-auth` (`deactivate_user`)
- Hard delete: handled here (`delete_user`) — cascades all auth and profile data
- Data export: handled here (`export_user_data`) — GDPR Article 20 compliance

**Profile fields:** display_name, bio, avatar_url, location, website, timezone.
Avatar URL is set by the app after uploading via `mcp-storage` — not uploaded here.

## Consequences

- Apps never need schema migrations to store new user settings
- GDPR delete is one tool call that removes everything
- Profile and preferences live in two tables — easy to extend either independently
