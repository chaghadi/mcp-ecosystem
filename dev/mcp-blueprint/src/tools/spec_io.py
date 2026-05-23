"""
spec_io.py — Read and write project spec files.

These helpers are used by every tool that needs to load or update a spec.
They are intentionally not MCP tools themselves — they are internal utilities.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import settings


def spec_dir(project_slug: str) -> Path:
    """Return the directory for a project's data files."""
    return settings.data_dir / "projects" / project_slug


def spec_path(project_slug: str) -> Path:
    """Return the path to a project's spec.json."""
    return spec_dir(project_slug) / "spec.json"


def audit_path(project_slug: str) -> Path:
    """Return the path to a project's audit.jsonl."""
    return spec_dir(project_slug) / "audit.jsonl"


def load_spec(project_slug: str) -> dict[str, Any]:
    """
    Load a project spec from disk.

    Returns the spec dict on success, or {"error": "..."} on failure.
    Callers must check for the "error" key before using the result.
    """
    path = spec_path(project_slug)
    if not path.exists():
        return {
            "error": (
                f"Project '{project_slug}' not found. "
                "Run init_project first, or check the slug spelling."
            )
        }
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"error": f"spec.json for '{project_slug}' is corrupted: {exc}"}


def save_spec(project_slug: str, spec: dict[str, Any]) -> None:
    """Write a spec dict back to disk, updating the updated_at timestamp."""
    spec["updated_at"] = datetime.now(timezone.utc).isoformat()
    path = spec_path(project_slug)
    path.write_text(json.dumps(spec, indent=2), encoding="utf-8")


def update_field(project_slug: str, field_path: str, value: Any) -> dict[str, Any]:
    """
    Update a single field in a project spec by dot-path (e.g. 'gates.pre_build').

    Returns {"ok": True} or {"error": "..."}.
    """
    spec = load_spec(project_slug)
    if "error" in spec:
        return spec

    parts = field_path.split(".")
    obj = spec
    for part in parts[:-1]:
        if not isinstance(obj.get(part), dict):
            obj[part] = {}
        obj = obj[part]
    obj[parts[-1]] = value

    save_spec(project_slug, spec)
    return {"ok": True}


def append_audit(project_slug: str, entry: dict[str, Any]) -> None:
    """Append one entry to the project's append-only audit.jsonl."""
    path = audit_path(project_slug)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def list_projects() -> list[str]:
    """Return slugs of all projects that have a spec.json."""
    projects_root = settings.data_dir / "projects"
    if not projects_root.exists():
        return []
    return [
        d.name
        for d in sorted(projects_root.iterdir())
        if d.is_dir() and (d / "spec.json").exists()
    ]
