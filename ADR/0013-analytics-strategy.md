# ADR-0013: Analytics Strategy — Postgres Events, Simple Funnels

**Date:** 2026-05-24
**Status:** Accepted
**Author:** chaghadi
**Brand:** mmiri28 solutions

---

## Context

Apps need event tracking, funnel analysis, and retention metrics.
Third-party analytics tools (Mixpanel, Amplitude) are expensive at scale
and send user data to external servers. We want to own our data.

## Decision

**Store events in Postgres.** A single `events` table with JSONB properties.
Simple, queryable, no extra infrastructure, data stays in our database.

**When to migrate to a dedicated analytics DB:**
If event volume exceeds 10M events/month, consider TimescaleDB (Postgres extension)
or ClickHouse. The schema and tool interface stay identical — just the storage changes.

**What mcp-analytics provides:**
- Event tracking (any app, any event name, JSONB properties)
- Funnel analysis (conversion rates between ordered steps)
- Retention cohorts (week-1, week-4, month-1)
- Per-user event history
- Aggregate counts by event name and date range

**What it does not provide:**
- Real-time dashboards (use a BI tool querying Postgres directly)
- A/B test assignment (handled by mcp-ab-test in the marketing category)

## Consequences

- Zero vendor lock-in — all data in our own Postgres
- Queryable with standard SQL for ad-hoc analysis
- Scales well to millions of events before needing migration
