# mcp-ecosystem — Setup Guide

**Brand:** mmiri28 solutions
**Owner:** chaghadi
**Repo:** github.com/chaghadi/mcp-ecosystem

---

## Prerequisites

Before anything, confirm these are installed on your Windows machine:

| Tool | Version | Check |
|------|---------|-------|
| Git | any | `git --version` |
| Python | 3.11+ | `python --version` |
| uv | any | `uv --version` |
| VS Code | any | open VS Code |
| Claude Code extension | latest | in VS Code extensions |

If `uv` is not installed:
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

## Step 1 — Clone the repo

```powershell
git clone https://github.com/chaghadi/mcp-ecosystem
cd mcp-ecosystem
```

---

## Step 2 — Run the setup script

```powershell
.\scripts\setup.ps1
```

This script handles everything automatically:
- Runs `uv sync` for every MCP that needs it
- Copies `.env.example` to `.env` for any new MCPs
- Reports which `.env` files still need credentials filled in

**Run this after every `git pull`.** It is safe to run multiple times.

---

## Step 3 — Verify the MCP runs

```powershell
uv run mcp-blueprint
```

You should see: `mcp-blueprint running on stdio`

Press `Ctrl+C` to stop.

---

## Step 4 — Open in VS Code

From the **repo root**:

```powershell
cd ..\..
code .
```

VS Code will read `.vscode/mcp.json` and Claude Code will automatically discover
`mcp-blueprint`. You should see it listed under Claude Code's MCP panel.

---

## Step 5 — Run the tests

```powershell
cd dev\mcp-blueprint
uv run pytest tests/ -v
```

All tests should pass before you start building anything.

---

## Step 6 — Initialize your first project

In Claude Code (or any MCP client), call:

```
init_project(
  project_name="YourAppName",
  brief="One paragraph describing what you're building.",
  stack="fullstack"
)
```

This creates `dev/mcp-blueprint/data/projects/{slug}/spec.json` and starts
the audit trail for that project.

---

## Adding a new MCP

When building the next MCP in the build order:

1. Create its folder under the correct category (`dev/`, `data/`, `business/`, etc.)
2. Follow the standard structure in each MCP's own `README.md`
3. Add it to `registry.json` with `"status": "active"` and its version
4. Add it to `.vscode/mcp.json` at the **ecosystem root** so Claude Code finds it
5. Write its first `CHANGELOG.md` entry

---

## Updating an existing MCP

1. Make your changes
2. Bump the version in `pyproject.toml` (or `package.json`) — follow semver (see ADR-0001)
3. Write a `CHANGELOG.md` entry explaining what changed and why
4. Update `registry.json` with the new version and `"updated"` date
5. Apps that depend on this MCP are **not** automatically updated — they choose when to pin to the new version

---

## Project data and backups

Project specs and audit logs live in `dev/mcp-blueprint/data/` — this folder is
git-ignored. Back it up by:
- Pushing to a private repo manually when needed, or
- Using `mcp-backup` (planned — see `registry.json`) once it is built

---

## Architecture decisions

All "why did we build it this way" decisions are documented in `ADR/`.
Read these before changing any foundational behaviour.
