# mcp-user-mgmt

**Version:** 0.1.0 | **Runtime:** Python 3.12 | **Depends on:** mcp-auth, mcp-postgres

User management MCP for mmiri28 solutions.
Profiles, flexible preferences, GDPR lifecycle, and user search.

---

## Tools

| Group | Tool | Description |
|-------|------|-------------|
| Profiles | `create_profile(user_id, ...)` | Create extended profile after register |
| Profiles | `get_profile(user_id)` | Full profile + auth fields |
| Profiles | `update_profile(user_id, fields)` | Update profile fields |
| Preferences | `get_preferences(user_id, app_slug)` | Get all or app-specific prefs |
| Preferences | `set_preference(user_id, key, value, app_slug)` | Set one key |
| Preferences | `set_preferences(user_id, prefs, app_slug)` | Set multiple keys |
| Preferences | `delete_preference(user_id, key, app_slug)` | Remove a key |
| Lifecycle | `delete_user(user_id, reason)` | GDPR hard delete |
| Lifecycle | `export_user_data(user_id)` | GDPR data export |
| Search | `search_users(query, app_slug, page, limit)` | Find users |
| Admin | `health_check()` | Check DB + table existence |
| Admin | `run_migrations()` | Apply schema migrations |

---

## Preferences model

Preferences are namespaced by app slug in a single JSONB column:

```json
{
  "global":      { "timezone": "Europe/Vienna", "language": "en" },
  "marketplace": { "theme": "dark", "email_notifications": true },
  "saas-tool":   { "sidebar_collapsed": false }
}
```

No migration needed to add new preference keys — just write them.

```
set_preference(user_id, "theme", "dark", app_slug="marketplace")
get_preferences(user_id, app_slug="marketplace")
→ { "theme": "dark", "email_notifications": true }
```

---

## Setup

```powershell
cd business\mcp-user-mgmt
uv sync
copy .env.example .env
# DATABASE_URL = same Supabase pooler URL as mcp-auth
```

Run migrations (requires mcp-auth migration to run first):
```
run_migrations() on mcp-user-mgmt
```
