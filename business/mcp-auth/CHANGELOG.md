# mcp-auth Changelog

## [0.1.0] — 2026-05-24 — chaghadi

**Initial build. mmiri28 solutions.**

### Added
**Auth:** `register`, `login`, `logout`, `refresh_access_token`, `verify_token`

**Roles:** `create_app`, `create_role`, `assign_role`, `revoke_role`,
`get_user_roles`, `list_app_roles`

**Users:** `get_user`, `update_user`, `deactivate_user`, `list_users`

**Admin:** `health_check`, `run_migrations`

**Stubs:** `oauth_redirect`, `oauth_callback`, `send_verification`, `verify_code`

### Schema (migration 0001)
Tables: `users`, `apps`, `app_roles`, `user_app_roles`, `oauth_accounts`, `refresh_tokens`

### Architecture decisions recorded
- ADR-0008: Auth Strategy (email/phone/username, JWT, app-scoped roles, Option C)

### Notes
- Uses `bcrypt` directly (not passlib — compatibility issue with bcrypt>=4.0)
- Access tokens: 15-min JWT. Refresh tokens: 30-day, stored hashed in Postgres
- Blacklist: revoked tokens in Redis until natural expiry
- Superadmin auto-assigned to `SUPERADMIN_EMAIL` on first register
