"""generate_catalog.py — build apps/mmiri/data/mcps.json from the ecosystem.

Reads registry.json for the MCP list, then introspects each server.py to
extract @mcp.tool() decorated functions. Writes a structured JSON the
mmiri frontend can render.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "registry.json"
OUT = ROOT / "apps" / "mmiri" / "data" / "mcps.json"

CATEGORY_ORDER = ["data", "business", "dev", "infra",
                   "marketing", "scheduling", "launch", "team"]

CATEGORY_BLURB = {
    "data":       "the source — postgres, redis, storage, search",
    "business":   "what every product needs — auth, users, billing, comms",
    "dev":        "developer workflow — scaffold, git, docker, tests, lint",
    "infra":      "where apps run — hosting, DNS, certs, monitoring, backups",
    "marketing":  "growth — social, content, SEO, email, A/B, press",
    "scheduling": "coordination — calendar, cron, releases, standups, time",
    "launch":     "to market — crypto, iOS, Android, Product Hunt, waitlists",
    "team":       "operations — Slack, docs, onboarding, code review, Figma",
}


def extract_tools(server_path: Path) -> list[str]:
    """Find every function decorated with @mcp.tool() in a server.py."""
    if not server_path.exists():
        return []
    text = server_path.read_text(encoding="utf-8", errors="ignore")
    # Match: @mcp.tool() ... def name(... or async def name(...
    return re.findall(
        r"@mcp\.tool\(\)\s*\n(?:async\s+)?def\s+([a-z_][a-z0-9_]*)\s*\(",
        text,
    )


def main():
    registry = json.loads(REGISTRY.read_text())
    mcps = registry["mcps"]

    by_category: dict[str, list[dict]] = {}

    for name, meta in mcps.items():
        if meta.get("status") != "active":
            continue
        category = meta["category"]
        path_to_server = ROOT / meta["path"] / "src" / "server.py"
        tools = extract_tools(path_to_server)

        by_category.setdefault(category, []).append({
            "name": name,
            "description": meta["description"],
            "tools": tools,
            "tool_count": len(tools),
            "depends_on": meta.get("depends_on", []),
            "needs_db": any("postgres" in d for d in meta.get("depends_on", [])),
        })

    # Order categories canonically; sort MCPs within each by name
    ordered = {}
    for cat in CATEGORY_ORDER:
        if cat in by_category:
            ordered[cat] = {
                "blurb": CATEGORY_BLURB.get(cat, ""),
                "mcps": sorted(by_category[cat], key=lambda m: m["name"]),
            }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(ordered, indent=2))

    total_mcps = sum(len(c["mcps"]) for c in ordered.values())
    total_tools = sum(m["tool_count"] for c in ordered.values() for m in c["mcps"])
    print(f"Wrote {OUT}")
    print(f"  Categories: {len(ordered)}")
    print(f"  MCPs: {total_mcps}")
    print(f"  Total tools across all MCPs: {total_tools}")


if __name__ == "__main__":
    main()
