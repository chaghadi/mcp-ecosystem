"""
check_spec_completeness.py — Score a project spec from 0-100.

Must reach 85 before gate_pre_build will pass. Run this often to see
what is still missing and what to work on next.
"""

from datetime import datetime, timezone
from typing import Any

from src.config import settings
from src.tools.spec_io import append_audit, load_spec, update_field

# Each key maps to a spec field check and its weight.
# Total weight = 100.
CHECKS: dict[str, dict[str, Any]] = {
    "brief_present": {
        "weight": 5,
        "label": "Brief written",
        "phase": 1,
        "field": "brief",
    },
    "prd_written": {
        "weight": 20,
        "label": "PRD written",
        "phase": 1,
        "field": "prd",
    },
    "tech_spec_written": {
        "weight": 15,
        "label": "Tech spec written",
        "phase": 1,
        "field": "tech_spec",
    },
    "api_contracts_defined": {
        "weight": 15,
        "label": "API contracts defined",
        "phase": 1,
        "field": "api_contracts",
        "is_list": True,
    },
    "schemas_defined": {
        "weight": 10,
        "label": "Database schemas defined",
        "phase": 1,
        "field": "schemas",
        "is_list": True,
    },
    "user_stories_written": {
        "weight": 10,
        "label": "User stories written",
        "phase": 1,
        "field": "user_stories",
        "is_list": True,
    },
    "design_tokens_generated": {
        "weight": 10,
        "label": "Design tokens generated",
        "phase": 2,
        "field": "design_tokens",
    },
    "components_defined": {
        "weight": 10,
        "label": "Components defined",
        "phase": 2,
        "field": "components",
        "is_list": True,
    },
    "wireframe_spec_written": {
        "weight": 3,
        "label": "Wireframe spec written",
        "phase": 2,
        "field": "wireframe_spec",
    },
    "style_guide_generated": {
        "weight": 2,
        "label": "Style guide generated",
        "phase": 2,
        "field": "style_guide",
    },
}

BUILD_GATE_THRESHOLD = 85


def _is_present(spec: dict, check: dict) -> bool:
    """Return True if the spec field for this check has meaningful content."""
    value = spec.get(check["field"])
    if check.get("is_list"):
        return isinstance(value, list) and len(value) > 0
    return value is not None and value != "" and value is not False


def run(project_slug: str) -> dict[str, Any]:
    """
    Score the completeness of a project spec (0-100).

    Checks every required section across Phase 1 (spec) and Phase 2 (design).
    Returns the score, a per-check breakdown, a gap list, and what to do next.

    Args:
        project_slug: The slug of the project (from init_project).

    Returns:
        Score, checks, gaps, readiness flags, and next recommended action.
    """
    spec = load_spec(project_slug)
    if "error" in spec:
        return spec

    # ── Score ─────────────────────────────────────────────────────────────────
    results: dict[str, bool] = {}
    score = 0
    for key, check in CHECKS.items():
        passed = _is_present(spec, check)
        results[key] = passed
        if passed:
            score += check["weight"]

    # ── Gaps ──────────────────────────────────────────────────────────────────
    gaps = [
        {"key": key, "label": CHECKS[key]["label"], "points": CHECKS[key]["weight"]}
        for key, passed in results.items()
        if not passed
    ]
    gaps.sort(key=lambda g: g["points"], reverse=True)  # highest-value gaps first

    # ── Readiness flags ───────────────────────────────────────────────────────
    phase_1_complete = all(
        results[k] for k, c in CHECKS.items() if c["phase"] == 1
    )
    phase_2_complete = all(
        results[k] for k, c in CHECKS.items() if c["phase"] == 2
    )
    build_ready = score >= BUILD_GATE_THRESHOLD

    # ── Points still available ────────────────────────────────────────────────
    points_remaining = sum(g["points"] for g in gaps)
    can_still_reach_threshold = (score + points_remaining) >= BUILD_GATE_THRESHOLD

    # ── Persist updated score to spec ─────────────────────────────────────────
    update_field(project_slug, "completeness_score", score)

    # ── Audit ─────────────────────────────────────────────────────────────────
    now = datetime.now(timezone.utc).isoformat()
    append_audit(
        project_slug,
        {
            "timestamp": now,
            "action": "check_spec_completeness",
            "project_slug": project_slug,
            "actor": settings.owner,
            "score": score,
            "build_ready": build_ready,
        },
    )

    # ── Next action message ───────────────────────────────────────────────────
    if build_ready:
        next_action = "Run gate_pre_build to unlock mcp-scaffold."
    elif gaps:
        top_gap = gaps[0]
        next_action = (
            f"Work on '{top_gap['label']}' next — worth {top_gap['points']} points."
        )
    else:
        next_action = "All sections complete."

    return {
        "ok": True,
        "project_slug": project_slug,
        "score": score,
        "max_score": 100,
        "build_gate_threshold": BUILD_GATE_THRESHOLD,
        "build_ready": build_ready,
        "phase_1_complete": phase_1_complete,
        "phase_2_complete": phase_2_complete,
        "can_reach_threshold": can_still_reach_threshold,
        "checks": results,
        "gaps": gaps,
        "next_action": next_action,
        "summary": (
            f"{score}/100 — {'✅ Ready to build' if build_ready else f'🔲 {BUILD_GATE_THRESHOLD - score} more points needed to unlock build gate'}."
        ),
    }
