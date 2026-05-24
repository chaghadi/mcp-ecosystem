"""server.py — mcp-changelog MCP server entry point."""

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from mcp.server.fastmcp import FastMCP
from src.config import settings

mcp = FastMCP(
    "mcp-changelog",
    instructions="Changelog management MCP for mmiri28 solutions. Generate entries, read changelogs, bump versions, generate release notes from git log.",
)


def _read_changelog(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _git_log(cwd: str, since_tag: str | None = None, limit: int = 20) -> list[str]:
    cmd = ["git", "log", f"--oneline", f"-{limit}"]
    if since_tag:
        cmd.append(f"{since_tag}..HEAD")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=10)
        if result.returncode == 0:
            return [l.strip() for l in result.stdout.splitlines() if l.strip()]
    except Exception:
        pass
    return []


@mcp.tool()
def get_changelog(mcp_name: str, category: str) -> dict[str, Any]:
    """
    Read the CHANGELOG.md for an MCP.

    Args:
        mcp_name: e.g. "mcp-auth"
        category: e.g. "business"
    """
    path = settings.ecosystem_root / category / mcp_name / "CHANGELOG.md"
    if not path.exists():
        return {"ok": False, "error": f"No CHANGELOG.md found for {mcp_name}"}
    return {"ok": True, "mcp": mcp_name, "content": path.read_text(encoding="utf-8")}


@mcp.tool()
def add_changelog_entry(
    mcp_name: str,
    category: str,
    version: str,
    added: list[str] | None = None,
    changed: list[str] | None = None,
    fixed: list[str] | None = None,
    breaking: list[str] | None = None,
) -> dict[str, Any]:
    """
    Add a new entry to an MCP's CHANGELOG.md.

    Args:
        mcp_name:  e.g. "mcp-auth"
        category:  e.g. "business"
        version:   Semver string e.g. "0.2.0"
        added:     List of added features.
        changed:   List of changed behaviours.
        fixed:     List of bug fixes.
        breaking:  List of breaking changes (triggers MAJOR bump).
    """
    path = settings.ecosystem_root / category / mcp_name / "CHANGELOG.md"
    if not path.exists():
        return {"ok": False, "error": f"No CHANGELOG.md found for {mcp_name}"}

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entry_lines = [f"\n## [{version}] — {now} — {settings.github_owner}\n"]

    if added:
        entry_lines.append("\n### Added\n" + "\n".join(f"- {a}" for a in added))
    if changed:
        entry_lines.append("\n### Changed\n" + "\n".join(f"- {c}" for c in changed))
    if fixed:
        entry_lines.append("\n### Fixed\n" + "\n".join(f"- {f}" for f in fixed))
    if breaking:
        entry_lines.append("\n### Breaking\n" + "\n".join(f"- {b}" for b in breaking))

    entry = "\n".join(entry_lines) + "\n"

    # Insert after the first line (title)
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)
    # Find insertion point — after first ## heading
    insert_at = 1
    for i, line in enumerate(lines):
        if line.startswith("## ") and i > 0:
            insert_at = i
            break

    new_content = "".join(lines[:insert_at]) + entry + "".join(lines[insert_at:])
    path.write_text(new_content, encoding="utf-8")

    return {"ok": True, "mcp": mcp_name, "version": version,
            "message": f"Added v{version} entry to CHANGELOG.md"}


@mcp.tool()
def get_version(mcp_name: str, category: str) -> dict[str, Any]:
    """Get the current version of an MCP from pyproject.toml."""
    pyproject = settings.ecosystem_root / category / mcp_name / "pyproject.toml"
    if not pyproject.exists():
        return {"ok": False, "error": f"No pyproject.toml found for {mcp_name}"}
    content = pyproject.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        return {"ok": False, "error": "Could not parse version from pyproject.toml"}
    return {"ok": True, "mcp": mcp_name, "version": match.group(1)}


@mcp.tool()
def bump_version(
    mcp_name: str, category: str, bump: str = "patch",
) -> dict[str, Any]:
    """
    Bump the version in pyproject.toml.

    Args:
        mcp_name: e.g. "mcp-auth"
        category: e.g. "business"
        bump:     "patch", "minor", or "major"
    """
    if bump not in ("patch", "minor", "major"):
        return {"ok": False, "error": "bump must be patch, minor, or major"}

    result = get_version(mcp_name, category)
    if not result["ok"]:
        return result

    current = result["version"]
    parts = [int(x) for x in current.split(".")]
    if bump == "patch":  parts[2] += 1
    elif bump == "minor": parts[1] += 1; parts[2] = 0
    elif bump == "major": parts[0] += 1; parts[1] = 0; parts[2] = 0

    new_version = ".".join(str(p) for p in parts)
    pyproject = settings.ecosystem_root / category / mcp_name / "pyproject.toml"
    content = pyproject.read_text(encoding="utf-8")
    new_content = re.sub(r'^version\s*=\s*"[^"]+"', f'version = "{new_version}"',
                         content, count=1, flags=re.MULTILINE)
    pyproject.write_text(new_content, encoding="utf-8")

    return {"ok": True, "mcp": mcp_name,
            "from": current, "to": new_version, "bump": bump}


@mcp.tool()
def generate_release_notes(
    mcp_name: str, category: str, since_tag: str | None = None,
) -> dict[str, Any]:
    """
    Generate release notes from recent git commits.

    Args:
        mcp_name:  The MCP to generate notes for.
        category:  MCP category.
        since_tag: Only include commits after this tag (e.g. "v0.1.0").
    """
    mcp_path = str(settings.ecosystem_root / category / mcp_name)
    commits = _git_log(mcp_path, since_tag)

    if not commits:
        return {"ok": True, "mcp": mcp_name,
                "notes": "No recent commits found.", "commits": []}

    notes_lines = [f"## Release notes — {mcp_name}\n"]
    for commit in commits:
        sha, _, msg = commit.partition(" ")
        notes_lines.append(f"- {msg} ({sha})")

    return {"ok": True, "mcp": mcp_name,
            "commit_count": len(commits),
            "notes": "\n".join(notes_lines),
            "commits": commits}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
