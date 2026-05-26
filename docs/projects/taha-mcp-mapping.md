# Taha — MCP Mapping

How each mmiri MCP participates in Taha, and **when** it fires.

## Development plane (fire when building/changing Taha)

| MCP | When it fires | What it does |
|-----|--------------|--------------|
| `mcp-blueprint` | Before every build session | Gates the build. `check_spec_completeness` must return 85+. `gate_pre_build` must pass before scaffold or code generation. |
| `mcp-scaffold` | Creating a new app in the ecosystem | `scaffold_web_app("taha-owner", mcps=["mcp-auth","mcp-postgres"])` — wires `.vscode/mcp.json` automatically. Use for v0.2 and all future apps. |
| `mcp-git-ops` | After any code change | `commit_and_push(message, files)` — keeps audit trail. |
| `mcp-test-runner` | Before every push to main | Runs 7 validation story tests + RLS tests. Blocks push if any fail. |
| `mcp-linter` | On every file save | TypeScript type check + ESLint. Zero warnings policy. |
| `mcp-env` | When adding new env vars | `set_secret("VITE_SUPABASE_ANON_KEY", value, app="taha-owner")` — never hardcode. |
| `mcp-deps` | When adding packages | Checks for vulnerabilities before `npm install`. |
| `mcp-changelog` | After every merged PR | Auto-generates CHANGELOG.md entry from commit messages + spec diff. |

## Operations plane (fire when deploying/monitoring Taha)

| MCP | When it fires | What it does |
|-----|--------------|--------------|
| `mcp-vercel` | Every push to main | `deploy(project="taha-client", env="production")` — deploys the client app public URL. |
| `mcp-monitor` | After first deploy | Registers client app URL for uptime checks every 5 minutes. |
| `mcp-cloudflare` | When custom domain added | DNS record creation + cache config for `taha.at`. |
| `mcp-ssl` | After domain attached | Validates SSL cert chain and expiry. Alerts at 30 days. |
| `mcp-backup` | Every Sunday 02:00 | `pg_dump` of Supabase to R2 storage. 30-day retention. |

## Runtime services plane (fire while Taha is running in production)

| MCP | Trigger | What it does |
|-----|---------|--------------|
| `mcp-notifications` | DB trigger on `shifts` UPDATE status=reassigned | Push notification to replacement employee. |
| `mcp-notifications` | DB trigger on `inventory_items` current_stock < min_stock | Push alert to manager. |
| `mcp-notifications` | DB trigger on `supply_reports` INSERT | Notifies manager of employee supply report. |
| `mcp-notifications` | Manager clicks "Send Receipt" in payroll page | Sends payslip notification to employee with gross pay, hours, week period. Employee receives in-app prompt to sign. |
| `mcp-analytics` | Every shift clock-in / clock-out | Logs `attendance.clock_in` and `attendance.clock_out` events. |
| `mcp-analytics` | Every expense recorded | Logs `expense.recorded` with category and amount. |
| `mcp-analytics` | Every service request submitted | Logs `service_request.created` event. |
| `mcp-analytics` | Employee signs payslip | Logs `payroll.signed` event with employee_id, week, gross_pay. |
| `mcp-auth` | Every login attempt | Validates phone+password, injects `app_role` into JWT. |
| `mcp-cron` | Sunday 10:00 Vienna | Nudges manager: "Neue Woche — Zeitplan erstellen?" |

## Payroll signature flow (detailed)

```
Manager (owner app)
  → clicks "Send Receipt" on employee row
  → sees confirmation modal: name, period, hours, gross pay
  → confirms → writes payroll_signatures row (status=pending)
  → writes notification row (type=payroll_receipt, metadata={gross_pay, hours, week})
  → mcp-notifications fires push to employee device

Employee (worker app)
  → sees red badge on Payroll tab
  → opens payslip card: period, hours, gross pay
  → clicks "Sign Receipt"
  → bottom sheet opens: receipt summary + typed name field (italic serif)
  → types full name → clicks "Sign & Confirm"
  → payroll_signatures row updated: status=signed, signed_name, signed_at
  → notification marked read
  → success screen shown

Manager (owner app, payroll page)
  → employee row shows green "Signed" badge
  → summary tiles: Signed / Awaiting / Not sent
```

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
9. mcp-scaffold.scaffold_web_app()       ← generate repo, wired to MCPs
10. Claude Code builds → mcp-test-runner validates
11. mcp-vercel.deploy()                  ← ship
12. mcp-monitor.register()               ← watch
```

Every app you build follows this 12-step flow.
Steps 1–9 and 11–12 are fully automated through MCPs.
You only write code in step 10.
