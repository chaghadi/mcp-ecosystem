# ADR-0004: Docker Images in GitHub Container Registry

**Date:** 2026-05-24
**Status:** Accepted
**Author:** chaghadi
**Brand:** mmiri28 solutions

---

## Context

Every MCP and app that needs a Docker image must be stored somewhere.
Options considered: Docker Hub, AWS ECR, DigitalOcean Container Registry,
GitHub Container Registry (ghcr.io).

## Decision

All Docker images are stored in **GitHub Container Registry** at
`ghcr.io/chaghadi/{image-name}`.

**Why:**
- Free for public repos — zero cost while building
- Authenticated automatically via `GITHUB_TOKEN` in Actions — no secrets to manage
- Images live alongside the code that produces them — one place to look
- Works natively with DigitalOcean App Platform and Droplets

**Image naming convention:**
- `ghcr.io/chaghadi/mcp-{name}` for MCP images
- `ghcr.io/chaghadi/app-{name}` for app images

**Tagging convention:**
- `latest` — current main branch build
- `v{semver}` — tagged releases (e.g. `v0.1.0`)
- `sha-{git-short-sha}` — every commit build (for rollback)

**Build trigger:**
GitHub Actions workflow per MCP/app, triggered on push to `main`
when files in that MCP/app's path change.

## Consequences

- No Docker Hub account needed
- Images are versioned alongside code via git tags
- Rolling back a deploy = pulling a previous `sha-*` tag
- If the repo ever goes private, image access needs a PAT configured in DigitalOcean
