# mcp-auth

**Version:** 0.1.0 | **Runtime:** Python 3.12 | **Image:** `ghcr.io/chaghadi/mcp-auth`

Auth MCP for mmiri28 solutions. Email/phone/username login, JWT tokens, app-scoped roles.

---

## Tools

| Group | Tool | Description |
|-------|------|-------------|
| Auth | `register(identifier, password, auth_method, app_slug, initial_role)` | Create account |
| Auth | `login(identifier, password, auth_method, app_slug)` | Authenticate, get tokens |
| Auth | `logout(refresh_token, access_token)` | Revoke tokens |
| Auth | `refresh_access_token(refresh_token)` | New access token |
| Auth | `verify_token(access_token, app_slug)` | Validate token, get roles |
| Roles | `create_app(slug, name)` | Register an app |
| Roles | `create_role(app_slug, role_name, description)` | Define a role |
| Roles | `assign_role(user_id, app_slug, role_name, ...)` | Assign role to user |
| Roles | `revoke_role(user_id, app_slug, role_name)` | Remove role |
| Roles | `get_user_roles(user_id, app_slug)` | Get user's roles |
| Roles | `list_app_roles(app_slug)` | List all roles for an app |
| Users | `get_user(identifier)` | Look up by id/email/phone/username |
| Users | `update_user(user_id, fields)` | Update user fields |
| Users | `deactivate_user(user_id)` | Soft delete |
| Users | `list_users(app_slug, role_name, page, limit)` | List with filters |
| Admin | `health_check()` | Check postgres + redis |
| Admin | `run_migrations()` | Apply Alembic migrations |
| Stubs | `oauth_redirect`, `oauth_callback` | Google OAuth (future) |
| Stubs | `send_verification`, `verify_code` | Email/phone verify (needs mcp-notifications) |

---

## Setup

```powershell
cd business\mcp-auth
uv sync
copy .env.example .env
# Fill in DATABASE_URL, REDIS_URL, JWT_SECRET, SUPERADMIN_EMAIL
```

**Generate JWT_SECRET:**
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

**Run migrations (creates all auth tables):**
```
run_migrations()
```

---

## Role model

```
superadmin (global)     ← you, cross-app access
    │
    └── user (global)   ← all registered users
            │
            ├── marketplace: seller, buyer, moderator
            ├── saas-tool:   owner, developer, viewer
            └── {any app}:   {any roles you define}
```

**verify_token** returns all of this in one call:
```json
{
  "user_id": "...",
  "global_role": "user",
  "app_roles": [{"app": "marketplace", "roles": ["seller"]}],
  "roles_in_app": ["seller"],
  "is_superadmin": false
}
```
