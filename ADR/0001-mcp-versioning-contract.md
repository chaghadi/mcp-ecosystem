# ADR-0001: MCP Versioning Contract

**Date:** 2026-05-23
**Status:** Accepted
**Author:** chaghadi
**Brand:** mmiri28 solutions

---

## Context

The ecosystem is a shared library of MCP servers consumed by multiple app repos.
Without a versioning contract, updating any MCP risks breaking apps silently.
We needed a rule that:
- Lets MCPs evolve freely
- Keeps apps stable until they explicitly choose to upgrade
- Makes it obvious when a breaking change has occurred

## Decision

Each MCP is versioned with **semver** (`MAJOR.MINOR.PATCH`) tracked in two places:
1. `registry.json` in this repo — the ecosystem-wide source of truth
2. `pyproject.toml` (or `package.json`) inside the MCP folder — the runtime version

**Apps pin to a specific MCP version** in their `.vscode/mcp.json` and their own dependency manifest.

**Version bump rules:**
- `PATCH` — bug fix, no tool signature changes
- `MINOR` — new tools added, existing tools unchanged (backward compatible)
- `MAJOR` — tool removed, renamed, or argument signature changed (breaking)

**Update flow:**
1. Developer updates the MCP, bumps version, writes a `CHANGELOG.md` entry
2. `registry.json` is updated in this repo
3. Apps receive no forced update — they remain on their pinned version
4. App developer reads the CHANGELOG, decides when to update their pin
5. They update `.vscode/mcp.json` and test before merging

## Consequences

- Apps never break from an MCP update they didn't ask for
- Each MCP's `CHANGELOG.md` becomes critical documentation — it must be kept accurate
- `registry.json` is the single place to see the current version of every MCP
- When onboarding a new team member, they can read `CHANGELOG.md` to understand the history of any MCP without asking anyone
