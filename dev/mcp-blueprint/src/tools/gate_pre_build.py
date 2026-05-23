"""
gate_pre_build.py — Gate check before mcp-scaffold can run.

Returns 'pass' or 'block'. Writes the result to the project's audit trail.
Nothing gets built until this returns 'pass'.
"""

from datetime import datetime, timezone
from typing import Any

from src.config import settings
from src.tools.spec_io import append_audit, load_spec, update_field

BUILD_GATE_THRESHOLD = 85


def run(project_slug: str) -> dict[str, Any]:
    """
    Validate that a project is ready to be built.

    Checks:
      - Completeness score ≥ 85
      - PRD is written
      - Tech spec is written

    Returns 'pass' or 'block' with the full list of blocking issues and
    non-blocking warnings. The result is written to the audit trail.

    Args:
        project_slug: The slug of the project (from init_project).

    Returns:
        result: 'pass' or 'block'
        blocks: Issues that must be resolved before building
        warnings: Non-blocking recommendations
    """
    spec = load_spec(project_slug)
    if "error" in spec:
        return spec

    score = spec.get("completeness_score", 0)
    blocks: list[str] = []
    warnings: list[str] = []

    # ── Hard blocks ───────────────────────────────────────────────────────────
    if score < BUILD_GATE_THRESHOLD:
        blocks.append(
            f"Completeness score is {score}/100. "
            f"Minimum required: {BUILD_GATE_THRESHOLD}. "
            f"Run check_spec_completeness to see what to fill in."
        )

    if not spec.get("prd"):
        blocks.append(
            "PRD is not written. Run write_prd before building."
        )

    if not spec.get("tech_spec"):
        blocks.append(
            "Tech spec is not written. Run write_tech_spec before building."
        )

    # ── Warnings (non-blocking) ───────────────────────────────────────────────
    if not spec.get("api_contracts"):
        warnings.append(
            "No API contracts defined. Strongly recommended before generating code."
        )

    if not spec.get("schemas"):
        warnings.append(
            "No database schemas defined. Recommended if this project uses a database."
        )

    if not spec.get("user_stories"):
        warnings.append(
            "No user stories written. Recommended for tracking work in GitHub Issues."
        )

    # ── Result ────────────────────────────────────────────────────────────────
    result = "pass" if not blocks else "block"
    now = datetime.now(timezone.utc).isoformat()

    # ── Persist gate result to spec ───────────────────────────────────────────
    update_field(
        project_slug,
        "gates.pre_build",
        {
            "result": result,
            "checked_at": now,
            "score": score,
            "blocks": blocks,
            "warnings": warnings,
        },
    )

    # ── Audit ─────────────────────────────────────────────────────────────────
    append_audit(
        project_slug,
        {
            "timestamp": now,
            "action": "gate_pre_build",
            "project_slug": project_slug,
            "actor": settings.owner,
            "result": result,
            "score": score,
            "blocks": blocks,
            "warnings": warnings,
        },
    )

    # ── Response ──────────────────────────────────────────────────────────────
    if result == "pass":
        message = (
            f"✅ Gate passed (score: {score}/100). "
            "mcp-scaffold may proceed. "
            f"{'⚠️  ' + str(len(warnings)) + ' warning(s) noted.' if warnings else ''}"
        ).strip()
    else:
        message = (
            f"🚫 Gate blocked (score: {score}/100). "
            f"Resolve {len(blocks)} blocking issue(s) before building."
        )

    return {
        "result": result,
        "project_slug": project_slug,
        "score": score,
        "blocks": blocks,
        "warnings": warnings,
        "checked_at": now,
        "message": message,
    }
