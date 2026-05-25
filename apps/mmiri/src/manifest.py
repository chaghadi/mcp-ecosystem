"""manifest.py — scans the ecosystem and builds the MCP manifest.

For each MCP in the registry, extracts the list of @mcp.tool() functions
and the first line of their docstrings. Used by mmiri to display tile content.
"""

import ast
import json
from pathlib import Path

ECOSYSTEM_ROOT = Path(__file__).resolve().parents[3]

# Section names — water/river metaphors describing what each category does
SECTION_NAMES = {
    "data":       ("Iyi",         "Sources",     "where every flow begins"),
    "business":   ("Ahia",        "Currents",    "auth, payments, comms"),
    "dev":        ("Ọrụ",         "Bedrock",     "the developer toolchain"),
    "infra":      ("Ụzọ",         "Channels",    "where apps run and travel"),
    "marketing":  ("Olu",         "Tributaries", "channels that feed growth"),
    "scheduling": ("Oge",         "Tides",       "the rhythm of time"),
    "launch":     ("Mmalite",     "Shores",      "where waters meet the world"),
    "team":       ("Otu",         "Confluence",  "where people meet"),
}

# MCPs that are live (configured + verified end-to-end)
LIVE = {
    "mcp-postgres", "mcp-redis", "mcp-storage",
    "mcp-auth", "mcp-user-mgmt", "mcp-analytics",
}

# MCPs that need external API keys before they can do real work
PENDING_CREDS = {
    "mcp-billing", "mcp-notifications",
    "mcp-git-ops", "mcp-scaffold", "mcp-docker-ops",
    "mcp-vercel", "mcp-digitalocean", "mcp-cloudflare",
    "mcp-social-post", "mcp-content-gen",
    "mcp-calendar",
    "mcp-coinbase", "mcp-appstore", "mcp-playstore", "mcp-product-hunt",
    "mcp-slack-ops", "mcp-figma-ops",
}


def _extract_tools(server_py: Path) -> list[dict]:
    """Parse a server.py file and return [{name, summary}] for each @mcp.tool()."""
    try:
        tree = ast.parse(server_py.read_text())
    except Exception:
        return []

    tools = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            is_mcp_tool = False
            if isinstance(decorator, ast.Call):
                func = decorator.func
                if isinstance(func, ast.Attribute) and func.attr == "tool":
                    is_mcp_tool = True
            elif isinstance(decorator, ast.Attribute) and decorator.attr == "tool":
                is_mcp_tool = True

            if is_mcp_tool:
                docstring = ast.get_docstring(node) or ""
                summary = docstring.strip().split("\n")[0].strip()
                tools.append({
                    "name": node.name,
                    "summary": summary[:160],
                })
                break
    return tools


def _status(mcp_name: str) -> str:
    if mcp_name in LIVE:
        return "live"
    if mcp_name in PENDING_CREDS:
        return "pending"
    return "ready"


def build_manifest() -> dict:
    """Scan the registry and build the full MCP manifest."""
    registry_path = ECOSYSTEM_ROOT / "registry.json"
    registry = json.loads(registry_path.read_text())

    sections = {}
    for mcp_name, meta in registry.get("mcps", {}).items():
        category = meta.get("category", "other")
        path = ECOSYSTEM_ROOT / meta.get("path", "")
        server_py = path / "src" / "server.py"
        tools = _extract_tools(server_py) if server_py.exists() else []

        sections.setdefault(category, []).append({
            "name": mcp_name,
            "version": meta.get("version", "0.1.0"),
            "description": meta.get("description", ""),
            "depends_on": meta.get("depends_on", []),
            "status": _status(mcp_name),
            "tool_count": len(tools),
            "tools": tools,
        })

    # Build ordered list of categories per SECTION_NAMES order
    ordered = []
    for cat, (igbo, label, sub) in SECTION_NAMES.items():
        mcps = sorted(sections.get(cat, []), key=lambda m: m["name"])
        ordered.append({
            "category": cat,
            "igbo": igbo,
            "label": label,
            "subtitle": sub,
            "count": len(mcps),
            "mcps": mcps,
        })

    totals = {
        "mcps": sum(s["count"] for s in ordered),
        "live": sum(1 for s in ordered for m in s["mcps"] if m["status"] == "live"),
        "ready": sum(1 for s in ordered for m in s["mcps"] if m["status"] == "ready"),
        "pending": sum(1 for s in ordered for m in s["mcps"] if m["status"] == "pending"),
        "tools_total": sum(m["tool_count"] for s in ordered for m in s["mcps"]),
    }

    return {"sections": ordered, "totals": totals}


if __name__ == "__main__":
    manifest = build_manifest()
    print(json.dumps(manifest, indent=2))
