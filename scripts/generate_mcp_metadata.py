"""generate_mcp_metadata.py

Scans the entire ecosystem and produces a JSON catalog of all 47 MCPs:
- name, category, description (from FastMCP instructions)
- tool list with one-line summaries
- credential status (live / no-creds / pending)

Output: apps/mmiri/src/static/mcps.json

Re-run this whenever MCPs are added, removed, or their tools change.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # mcp-ecosystem root
OUTPUT = ROOT / "apps" / "mmiri" / "src" / "static" / "mcps.json"

CATEGORIES = ["data", "business", "dev", "infra",
              "marketing", "scheduling", "launch", "team"]

# MCPs already wired with real credentials and verified
LIVE_MCPS = {"mcp-postgres", "mcp-redis", "mcp-storage",
             "mcp-auth", "mcp-user-mgmt"}


def extract_tools(server_py: Path) -> list[dict]:
    """Pull every @mcp.tool() function out of a server.py."""
    content = server_py.read_text()
    pattern = re.compile(
        r'@mcp\.tool\(\)\s*\n\s*def\s+(\w+)\s*\([^)]*\)[^:]*:\s*'
        r'(?:"""([^"]+?)""")?',
        re.DOTALL,
    )
    tools = []
    for match in pattern.finditer(content):
        name = match.group(1)
        docstring = (match.group(2) or "").strip()
        summary = docstring.split("\n")[0].strip() if docstring else ""
        tools.append({"name": name, "summary": summary})
    return tools


def extract_description(server_py: Path) -> str:
    """Pull the `instructions=` argument from the FastMCP() constructor."""
    content = server_py.read_text()
    match = re.search(
        r'FastMCP\s*\(\s*[^,)]+,\s*instructions\s*=\s*["\']([^"\']+)["\']',
        content, re.DOTALL,
    )
    if match:
        return match.group(1).strip()
    # Fallback to module docstring
    match = re.search(r'^"""([^"]+?)"""', content, re.DOTALL)
    return match.group(1).strip().split("\n")[0] if match else ""


def detect_status(mcp_dir: Path) -> str:
    """live (already wired), no-creds (works without API keys), or pending."""
    if mcp_dir.name in LIVE_MCPS:
        return "live"

    env_example = mcp_dir / ".env.example"
    if not env_example.exists():
        return "no-creds"

    lines = env_example.read_text().splitlines()
    non_comment = [l for l in lines if l.strip() and not l.lstrip().startswith("#")]

    if not non_comment:
        return "no-creds"

    # If the only required var is DATABASE_URL (already configured), it's no-creds
    if all("DATABASE_URL" in l for l in non_comment):
        return "no-creds"

    return "pending"


def main():
    catalog = {}
    for category in CATEGORIES:
        cat_dir = ROOT / category
        if not cat_dir.exists():
            continue
        for mcp_dir in sorted(cat_dir.iterdir()):
            if not (mcp_dir.is_dir() and mcp_dir.name.startswith("mcp-")):
                continue
            server_py = mcp_dir / "src" / "server.py"
            if not server_py.exists():
                continue

            catalog[mcp_dir.name] = {
                "name": mcp_dir.name,
                "category": category,
                "description": extract_description(server_py),
                "tools": extract_tools(server_py),
                "status": detect_status(mcp_dir),
            }

    # Group by category for the hub UI
    by_category = {}
    for cat in CATEGORIES:
        by_category[cat] = [m for m in catalog.values() if m["category"] == cat]

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_mcps": len(catalog),
        "categories": CATEGORIES,
        "by_category": by_category,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, indent=2))

    # Summary
    print(f"\nGenerated metadata for {len(catalog)} MCPs")
    print(f"Output: {OUTPUT.relative_to(ROOT)}\n")
    for cat in CATEGORIES:
        mcps = by_category[cat]
        live = sum(1 for m in mcps if m["status"] == "live")
        no_creds = sum(1 for m in mcps if m["status"] == "no-creds")
        pending = sum(1 for m in mcps if m["status"] == "pending")
        tool_count = sum(len(m["tools"]) for m in mcps)
        print(f"  {cat:11} {len(mcps)} MCPs  ·  {tool_count} tools  ·  "
              f"live={live} ready={no_creds} pending={pending}")


if __name__ == "__main__":
    main()
