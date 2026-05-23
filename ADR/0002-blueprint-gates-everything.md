# ADR-0002: mcp-blueprint Gates All Builds and Deployments

**Date:** 2026-05-23
**Status:** Accepted
**Author:** chaghadi
**Brand:** mmiri28 solutions

---

## Context

In early-stage product development, it is easy to start building before a project
is properly specified. This leads to rework, scope creep, and no audit trail of
why decisions were made. We needed a mechanism that enforces discipline without
slowing down motivated developers.

## Decision

`mcp-blueprint` is the **only** MCP that can block other MCPs from running.
It owns the following gates:

**`gate_pre_build`** — must return `pass` before `mcp-scaffold` creates any code.
Requires:
- Spec completeness score ≥ 85/100
- PRD written
- Tech spec written

**`gate_pre_deploy`** — must return `pass` before `mcp-vercel` or `mcp-digitalocean`
deploys anything. Requires:
- `gate_pre_build` previously passed
- Implementation matches API contracts (checked via spec diff)

Both gate results are written to the project's `audit.jsonl` — an append-only log
that records every gate decision with a timestamp and the actor who triggered it.

**Completeness scoring:**
| Section             | Weight |
|---------------------|--------|
| Brief present       | 5      |
| PRD written         | 20     |
| Tech spec written   | 15     |
| API contracts       | 15     |
| DB schemas          | 10     |
| User stories        | 10     |
| Design tokens       | 10     |
| Components defined  | 10     |
| Wireframe spec      | 3      |
| Style guide         | 2      |
| **Total**           | **100** |

## Consequences

- No app can be built without a spec. This is intentional.
- The audit trail answers "who approved this build/deploy and when" without
  anyone having to remember or explain it.
- `mcp-blueprint` must be the first MCP built. Everything else depends on it.
- The 85/100 threshold is deliberately high — it forces the important sections
  (PRD, tech spec, API contracts) to be written before code is generated.
