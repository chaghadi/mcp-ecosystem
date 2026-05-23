"""
init_project.py — Initialize a new project spec from a plain-language brief.

This is Phase 1, Step 0. It must be called before any other mcp-blueprint tool.
It creates the project folder, writes spec.json, and starts the audit trail.
"""

import json
import re
from datetime import datetime, timezone
from typing import Any

from src.config import settings
from src.tools.spec_io import append_audit, audit_path, save_spec, spec_dir, spec_path

VALID_STACKS = {"web", "backend", "mobile", "fullstack"}


def _slugify(name: str) -> str:
    """Convert a project name to a lowercase hyphenated slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def run(
    brief: str,
    project_name: str,
    stack: str = "fullstack",
) -> dict[str, Any]:
    """
    Initialize a new project spec from a plain-language brief.

    Creates:
      data/projects/{slug}/spec.json   — the project spec
      data/projects/{slug}/audit.jsonl — the audit trail (append-only)

    Args:
        brief:        Plain-language description of what you're building.
        project_name: Human-readable name (e.g. "TaskFlow"). Used to derive the slug.
        stack:        One of "web" | "backend" | "mobile" | "fullstack".

    Returns:
        The created spec summary plus next steps, or an error dict.
    """
    # ── Validate ──────────────────────────────────────────────────────────────
    if not brief or not brief.strip():
        return {"error": "brief cannot be empty. Write one paragraph describing what you're building."}

    if not project_name or not project_name.strip():
        return {"error": "project_name cannot be empty."}

    if stack not in VALID_STACKS:
        return {
            "error": f"Invalid stack '{stack}'. Must be one of: {', '.join(sorted(VALID_STACKS))}."
        }

    slug = _slugify(project_name)
    if not slug:
        return {
            "error": (
                f"project_name '{project_name}' produced an empty slug. "
                "Use a plain name like 'TaskFlow' or 'My App'."
            )
        }

    # ── Guard: project must not already exist ─────────────────────────────────
    project_dir = spec_dir(slug)
    if project_dir.exists() and spec_path(slug).exists():
        return {
            "error": (
                f"Project '{slug}' already exists. "
                "Use a different project_name, or delete the existing project's folder first."
            )
        }

    project_dir.mkdir(parents=True, exist_ok=True)

    # ── Build spec ────────────────────────────────────────────────────────────
    now = datetime.now(timezone.utc).isoformat()

    spec: dict[str, Any] = {
        "schema_version": "1.0",
        "project_slug": slug,
        "project_name": project_name,
        "brand": settings.brand,
        "owner": settings.owner,
        "created_at": now,
        "updated_at": now,
        "spec_version": "0.1.0",
        "status": "draft",
        "stack": stack,
        # ── Phase 1: Specification ────────────────────────────────────────────
        "brief": brief.strip(),
        "prd": None,
        "tech_spec": None,
        "api_contracts": [],
        "schemas": [],
        "user_stories": [],
        # ── Phase 2: Design ───────────────────────────────────────────────────
        "design_tokens": None,
        "components": [],
        "wireframe_spec": None,
        "style_guide": None,
        # ── Phase 3: Gates ────────────────────────────────────────────────────
        "completeness_score": 5,  # Brief present = 5 points
        "gates": {
            "pre_build": None,
            "pre_deploy": None,
        },
    }

    save_spec(slug, spec)

    # ── Start audit trail ─────────────────────────────────────────────────────
    append_audit(
        slug,
        {
            "timestamp": now,
            "action": "init_project",
            "project_slug": slug,
            "actor": settings.owner,
            "detail": f"Project '{project_name}' initialized. stack={stack}.",
        },
    )

    return {
        "ok": True,
        "project_slug": slug,
        "project_name": project_name,
        "brand": settings.brand,
        "owner": settings.owner,
        "stack": stack,
        "spec_path": str(spec_path(slug)),
        "created_at": now,
        "completeness_score": 5,
        "status": "draft",
        "next_steps": [
            "1. write_prd(project_slug) — generate a Product Requirements Document from your brief.",
            "2. write_tech_spec(project_slug) — derive the technical spec from the PRD.",
            "3. define_api_contracts(project_slug) — generate OpenAPI 3.0 contracts.",
            "4. define_schema(project_slug) — generate the database schema.",
            "5. write_user_stories(project_slug) — generate epics and stories.",
            "6. check_spec_completeness(project_slug) — score your spec. Target: 85+.",
            "7. gate_pre_build(project_slug) — unlock mcp-scaffold when score ≥ 85.",
        ],
    }
