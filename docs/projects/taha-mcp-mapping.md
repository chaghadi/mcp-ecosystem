# Taha — MCP Mapping

How each mmiri MCP participates in Taha — across the development, operations, and runtime planes.

## Development plane (fires when building/changing Taha)

| MCP | When it fires | What it does |
|-----|--------------|--------------|
| `mcp-blueprint` | Before every build session | Gates the build. `gate_pre_build` must pass before scaffold or code generation. |
| `mcp-scaffold` | Creating a new app | `scaffold_web_app(name, mcps=[...])` — wires `.vscode/mcp.json` automatically. |
| `mcp-git-ops` | After any code change | `commit_and_push(message, files)` — keeps audit trail. |
| `mcp-test-runner` | Before every push to main | Runs validation tests + RLS tests. Blocks push if any fail. |
| `mcp-linter` | On every file save | TypeScript check + ESLint. Zero warnings policy. |
| `mcp-env` | When adding env vars | `set_secret("VITE_SUPABASE_ANON_KEY", value, app="taha-owner")` — never hardcode. |
| `mcp-deps` | When adding packages | Vulnerability scan before `npm install`. |
| `mcp-changelog` | After every merged PR | Auto-generates CHANGELOG.md from commits + spec diff. |

## Operations plane (fires when deploying/monitoring)

| MCP | When it fires | What it does |
|-----|--------------|--------------|
| `mcp-vercel` | Every push to main | `deploy(project="taha-client", env="production")`. |
| `mcp-monitor` | After first deploy | Uptime checks every 5 minutes on client app URL. |
| `mcp-cloudflare` | When custom domain added | DNS + cache config for `taha.at`. |
| `mcp-ssl` | After domain attached | SSL cert chain + expiry monitoring. |
| `mcp-backup` | Every Sunday 02:00 | `pg_dump` of Supabase to R2 storage. 30-day retention. |

## Runtime services plane (fires while Taha is running in production)

| MCP | Trigger | What it does |
|-----|---------|--------------|
| `mcp-notifications` | Manager clicks "Send Receipt" | Push notification to employee with payslip details. |
| `mcp-notifications` | DB trigger on `shifts` status=reassigned | Notification to replacement employee. |
| `mcp-notifications` | DB trigger on `inventory_items` low stock | Alert to Sonja. |
| `mcp-notifications` | DB trigger on `supply_reports` INSERT | Notification to Sonja. |
| `mcp-analytics` | Every clock-in / clock-out | Logs `attendance.clock_in` / `attendance.clock_out`. |
| `mcp-analytics` | Every expense recorded | Logs `expense.recorded` with category and amount. |
| `mcp-analytics` | Every service request submitted | Logs `service_request.created`. |
| `mcp-analytics` | Employee signs payslip | Logs `payroll.signed` with employee_id, week, gross_pay. |
| `mcp-auth` | Every login attempt | Validates credentials, injects `app_role` into JWT. |
| `mcp-cron` | Sunday 10:00 Vienna | Nudges Sonja: "Neue Woche — Zeitplan erstellen?" |

## Payroll signature flow

```
Manager (owner app, Payroll page)
  → "Send Receipt" button on employee row with gross > 0
  → confirmation modal shows name, period, hours, rate, gross
  → confirm → writes payroll_signatures (status=pending) + notifications row
  → mcp-notifications fires push to employee

Employee (worker app, Lohn tab)
  → red badge on tab when notification arrives
  → payslip card: period + gross pay + hours
  → "Unterschreiben" → bottom sheet with receipt summary
  → types full name in italic serif field
  → "Sign & Confirm" → payroll_signatures status=signed, signed_name, signed_at
  → notification marked read → success screen with payment confirmation

Manager (owner app, refresh Payroll)
  → green "Signed" badge appears on that employee row
```

## Why these MCPs, why not others

**Used:** blueprint, scaffold, git-ops, test-runner, linter, env, deps, changelog, vercel, monitor, cloudflare, ssl, backup, notifications, analytics, auth, cron, postgres, storage.

**Not used in Taha v1:**
- `mcp-billing` — no payment processing or Stripe integration
- `mcp-search` — dataset too small to need indexed search
- `mcp-webhooks` — no third-party webhooks in v1
- `mcp-user-mgmt` — Supabase Auth handles user creation directly
- Marketing/launch MCPs (social, SEO, campaigns, press) — single B2B trial, no marketing surface

## The 12-step build flow (every future app)

```
1. mcp-blueprint.init_project()          register the idea
2. mcp-blueprint.write_prd()             what
3. mcp-blueprint.write_tech_spec()       how
4. mcp-blueprint.define_api_contracts()  API surface
5. mcp-blueprint.define_schema()         database
6. mcp-blueprint.write_user_stories()    acceptance
7. mcp-blueprint.check_spec_completeness must return 85+
8. mcp-blueprint.gate_pre_build()        must return "pass"
9. mcp-scaffold.scaffold_web_app()       generate repo, MCPs pre-wired
10. Code → mcp-test-runner validates
11. mcp-vercel.deploy()                  ship
12. mcp-monitor.register()               watch
```

Steps 1-9 and 11-12 are automated. You only write code in step 10.
