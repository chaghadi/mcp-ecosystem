"""catalog.py — discover all MCPs in the ecosystem and their tools.

Walks the ecosystem directory, parses each src/server.py via AST,
extracts @mcp.tool()-decorated functions and their docstrings.
Also reports a coarse credential-configuration status by inspecting
each MCP's .env file (presence + whether placeholders are still in it).
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

ECOSYSTEM_ROOT = Path(__file__).resolve().parents[3]

CATEGORIES = [
    "data", "business", "dev", "infra",
    "marketing", "scheduling", "launch", "team",
]

# MCPs that legitimately need no external credentials
# (they either run on the shared Postgres or do pure computation)
NO_CREDS_NEEDED = {
    "mcp-blueprint", "mcp-env", "mcp-test-runner", "mcp-linter",
    "mcp-changelog", "mcp-deps", "mcp-ssl", "mcp-seo",
}


def _extract_tools(server_file: Path) -> list[dict[str, str]]:
    """Parse a server.py and return [{"name": ..., "doc": ...}, ...]."""
    if not server_file.exists():
        return []
    try:
        tree = ast.parse(server_file.read_text(encoding="utf-8"))
    except SyntaxError:
        return []

    tools = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        # Look for @mcp.tool() or @mcp.tool decorators
        for dec in node.decorator_list:
            target = dec.func if isinstance(dec, ast.Call) else dec
            if isinstance(target, ast.Attribute) and target.attr == "tool":
                doc = ast.get_docstring(node) or ""
                first_line = doc.split("\n")[0].strip()
                tools.append({
                    "name": node.name,
                    "doc": first_line[:140] if first_line else "",
                })
                break
    return tools


def _credential_status(mcp_dir: Path) -> str:
    """Heuristic: returns 'configured' | 'pending' | 'no_creds_needed'."""
    if mcp_dir.name in NO_CREDS_NEEDED:
        return "no_creds_needed"

    env_file = mcp_dir / ".env"
    if not env_file.exists():
        return "pending"

    try:
        content = env_file.read_text(encoding="utf-8")
    except OSError:
        return "pending"

    # Look for real lines (not comments, not blank, not placeholder "your-...")
    has_real_value = False
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        _, _, value = line.partition("=")
        value = value.strip().strip('"').strip("'")
        if value and "your-" not in value.lower() and "[password]" not in value.lower():
            has_real_value = True
            break

    return "configured" if has_real_value else "pending"


def _read_description(mcp_dir: Path) -> str:
    """Pull the description from pyproject.toml."""
    pyp = mcp_dir / "pyproject.toml"
    if not pyp.exists():
        return ""
    try:
        for line in pyp.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("description"):
                _, _, value = line.partition("=")
                return value.strip().strip('"').strip("'")
    except OSError:
        pass
    return ""


def discover_mcps() -> dict[str, Any]:
    """Walk the ecosystem and return the full catalog."""
    catalog: dict[str, list[dict[str, Any]]] = {}
    total_mcps = 0
    total_tools = 0
    status_counts = {"configured": 0, "pending": 0, "no_creds_needed": 0}

    for cat in CATEGORIES:
        cat_dir = ECOSYSTEM_ROOT / cat
        if not cat_dir.exists():
            continue
        catalog[cat] = []
        for mcp_dir in sorted(cat_dir.iterdir()):
            if not mcp_dir.is_dir() or not mcp_dir.name.startswith("mcp-"):
                continue
            tools = _extract_tools(mcp_dir / "src" / "server.py")
            status = _credential_status(mcp_dir)
            desc = _read_description(mcp_dir)
            catalog[cat].append({
                "name": mcp_dir.name,
                "description": desc,
                "tools": tools,
                "tool_count": len(tools),
                "status": status,
            })
            total_mcps += 1
            total_tools += len(tools)
            status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "categories": catalog,
        "totals": {
            "mcps": total_mcps,
            "tools": total_tools,
            "categories": len(catalog),
            "configured": status_counts["configured"],
            "pending": status_counts["pending"],
            "no_creds_needed": status_counts["no_creds_needed"],
        },
    }


if __name__ == "__main__":
    import json
    print(json.dumps(discover_mcps()["totals"], indent=2))
