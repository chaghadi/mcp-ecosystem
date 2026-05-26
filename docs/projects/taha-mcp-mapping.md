# Taha — MCP Mapping

How each mmiri MCP participates in Taha, and **when** it fires.

## Development plane (fire when building/changing Taha)

| MCP | When it fires | What it does |
|-----|--------------|--------------|
| `mcp-blueprint` | Before every build session | Gates the build. `check_spec_completeness` must return 85+. `gate_pre_build` must pass before scaffold or code generation. |
| `mcp-scaffold` | Creating a new app in the ecosystem | Should be called via `scaffold_web_app("taha-owner", mcps=["mcp-auth","mcp-postgres"])` — this wires the correct `.vscode/mcp.json` automatically. Use for v0.2 and all future apps. |
| `mcp-git-ops` | After any code change | Claude Code calls `commit_and_push(message, files)` instead of raw `git` commands. Keeps audit trail. |
| `mcp-test-runner` | Before every push to main | Runs 7 validation story tests + RLS tests. Blocks push if any fail. |
| `mcp-linter` | On every file save | TypeScript type check + ESLint. Zero warnings policy. |
| `mcp-env` | When adding new env vars | `set_secret("VITE_SUPABASE_ANON_KEY", value, app="taha-owner")` — never hardcode. |
| `mcp-deps` | When adding packages | Checks for vulnerabilities before `npm install`. |
| `mcp-changelog` | After every merged PR | Auto-generates CHANGELOG.md entry from commit messages + spec diff. |

## Operations plane (fire when deploying/monitoring Taha)

| MCP | When it fires | What it does |
|-----|--------------|--------------|
| `mcp-vercel` | Every push to main | `deploy(project="taha-client", env="production")` — deploys the client app public URL. |
| `mcp-monitor` | After first deploy | Registers `https://taha-client.vercel.app` for uptime checks every 5 minutes. |
| `mcp-cloudflare` | When custom domain added | DNS record creation + cache config for `taha.at`. |
| `mcp-ssl` | After domain attached | Validates SSL cert chain and expiry. Alerts at 30 days. |
| `mcp-backup` | Every Sunday 02:00 | `pg_dump` of Supabase to R2 storage. 30-day retention. |

## Runtime services plane (fire while Taha is running in production)

| MCP | Trigger | What it does |
|-----|---------|--------------|
| `mcp-notifications` | DB trigger on `shifts` UPDATE status=reassigned | Sends push notification to replacement employee. |
| `mcp-notifications` | DB trigger on `inventory_items` current_stock < min_stock | Sends push alert to manager. |
| `mcp-notifications` | DB trigger on `supply_reports` INSERT | Notifies manager of employee supply report. |
| `mcp-analytics` | Every shift clock-in / clock-out | Logs `attendance.clock_in` and `attendance.clock_out` events. |
| `mcp-analytics` | Every expense recorded | Logs `expense.recorded` with category and amount. |
| `mcp-analytics` | Every service request submitted | Logs `service_request.created` event. |
| `mcp-cron` | Sunday 10:00 Vienna | Nudges manager: "Neue Woche — Zeitplan erstellen?" |
| `mcp-cron` | Friday 16:00 Vienna | Nudges manager: "Wochenlohn bereit zum Export." |
| `mcp-auth` | Every login attempt | Validates phone+password, injects `app_role` into JWT. |

## The correct build flow for ALL future apps

```
1. mcp-blueprint.init_project()          ← register the idea
2. mcp-blueprint.write_prd()             ← define what you're building
3. mcp-blueprint.write_tech_spec()       ← define how
4. mcp-blueprint.define_api_contracts()  ← define the API surface
5. mcp-blueprint.define_schema()         ← define the database
6. mcp-blueprint.write_user_stories()    ← define acceptance criteria
7. mcp-blueprint.check_spec_completeness() → must return 85+
8. mcp-blueprint.gate_pre_build()        → must return "pass"
9. mcp-scaffold.scaffold_web_app()       ← generate the repo, wired to MCPs
10. Claude Code builds → mcp-test-runner validates
11. mcp-vercel.deploy()                  ← ship
12. mcp-monitor.register()               ← watch
```

Every app you ever build follows this 12-step flow.
The MCPs handle steps 1-9 and 11-12 automatically.
You only write code in step 10.
