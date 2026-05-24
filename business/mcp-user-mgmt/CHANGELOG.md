# mcp-user-mgmt Changelog

## [0.1.0] — 2026-05-24 — chaghadi

**Initial build. mmiri28 solutions.**

### Added
**Profiles:** `create_profile`, `get_profile`, `update_profile`

**Preferences:** `get_preferences`, `set_preference`, `set_preferences`, `delete_preference`
- Flexible JSONB storage namespaced by app slug
- No schema migrations needed to add new preference keys

**Lifecycle:** `delete_user` (GDPR erasure), `export_user_data` (GDPR Article 20)

**Search:** `search_users` — by display name, email, username, phone

**Admin:** `health_check`, `run_migrations`

### Schema (migration 0001)
- `user_profiles` — display_name, bio, avatar_url, location, website, timezone
- `user_preferences` — JSONB column with GIN index for fast lookups

### Architecture decisions recorded
- ADR-0009: User Management Strategy (JSONB preferences, GDPR lifecycle)
