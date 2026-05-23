"""
audit_trail.py — Read the full audit trail for a project.

The audit trail is an append-only JSONL file. Every tool that changes
state writes an entry. This tool reads it back for review.
"""

import json
from typing import Any

from src.tools.spec_io import audit_path, list_projects, spec_dir


def run(project_slug: str) -> dict[str, Any]:
    """
    Return the full audit trail for a project.

    The audit trail records every action taken on a project:
    who did it, when, what the result was. It is append-only and never edited.

    Args:
        project_slug: The slug of the project (from init_project).

    Returns:
        All audit entries in chronological order, plus a summary.
    """
    path = audit_path(project_slug)

    if not spec_dir(project_slug).exists():
        return {
            "error": (
                f"Project '{project_slug}' not found. "
                "Run init_project first, or check the slug spelling."
            )
        }

    if not path.exists():
        return {
            "ok": True,
            "project_slug": project_slug,
            "total_entries": 0,
            "entries": [],
            "summary": "No audit entries yet.",
        }

    entries: list[dict[str, Any]] = []
    corrupt_lines = 0

    with path.open("r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                corrupt_lines += 1

    # ── Build a human-readable summary ───────────────────────────────────────
    action_counts: dict[str, int] = {}
    for entry in entries:
        action = entry.get("action", "unknown")
        action_counts[action] = action_counts.get(action, 0) + 1

    last_entry = entries[-1] if entries else None
    gate_results = [e for e in entries if "result" in e and "gate" in e.get("action", "")]

    summary_parts = [f"{count}× {action}" for action, count in sorted(action_counts.items())]

    return {
        "ok": True,
        "project_slug": project_slug,
        "total_entries": len(entries),
        "corrupt_lines": corrupt_lines,
        "entries": entries,
        "action_summary": action_counts,
        "last_action": last_entry,
        "gate_decisions": gate_results,
        "summary": f"{len(entries)} entries: {', '.join(summary_parts)}." if summary_parts else "No entries.",
    }


def run_list_projects() -> dict[str, Any]:
    """
    List all projects that have been initialized.

    Returns slugs and their last audit entry (if any).
    """
    slugs = list_projects()
    projects = []

    for slug in slugs:
        path = audit_path(slug)
        last_entry = None

        if path.exists():
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            if lines:
                try:
                    last_entry = json.loads(lines[-1])
                except json.JSONDecodeError:
                    pass

        projects.append(
            {
                "project_slug": slug,
                "last_action": last_entry.get("action") if last_entry else None,
                "last_actor": last_entry.get("actor") if last_entry else None,
                "last_timestamp": last_entry.get("timestamp") if last_entry else None,
            }
        )

    return {
        "ok": True,
        "total_projects": len(projects),
        "projects": projects,
    }
