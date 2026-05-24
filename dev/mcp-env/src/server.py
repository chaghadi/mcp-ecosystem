"""server.py — mcp-env MCP server entry point.

Manages .env files across apps and MCPs.
Validates required variables, generates .env from templates,
shows what's set vs missing across the ecosystem.
"""

import os
import re
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from src.config import settings

mcp = FastMCP(
    "mcp-env",
    instructions="Environment variable management for mmiri28 solutions. Scan, validate, and generate .env files across all MCPs and apps.",
)


def _read_env_file(path: Path) -> dict[str, str]:
    """Parse a .env file into a dict, skipping comments and blanks."""
    result = {}
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            result[key.strip()] = val.strip()
    return result


def _read_env_example(path: Path) -> list[str]:
    """Return required variable names from a .env.example file."""
    keys = []
    if not path.exists():
        return keys
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key = line.split("=")[0].strip()
            if key:
                keys.append(key)
    return keys


@mcp.tool()
def scan_ecosystem() -> dict[str, Any]:
    """
    Scan all MCPs in the ecosystem and report .env status.

    Shows which MCPs have .env files, which are missing,
    and which have unfilled placeholder values.
    """
    root = settings.ecosystem_root
    categories = ["dev", "data", "business", "infra", "marketing", "scheduling", "launch", "team"]

    results = []
    for cat in categories:
        cat_path = root / cat
        if not cat_path.exists():
            continue
        for mcp_dir in sorted(cat_path.iterdir()):
            if not mcp_dir.is_dir():
                continue
            env_example = mcp_dir / ".env.example"
            env_file = mcp_dir / ".env"
            if not env_example.exists():
                continue

            required_keys = _read_env_example(env_example)
            if not required_keys:
                continue

            if not env_file.exists():
                status = "missing"
                missing_keys = required_keys
                set_keys = []
            else:
                current = _read_env_file(env_file)
                placeholders = ["your-", "change-this", "placeholder", "[PASSWORD]", "[YOUR-"]
                set_keys = [k for k in required_keys if k in current and
                            not any(p in current[k].lower() for p in placeholders)]
                missing_keys = [k for k in required_keys if k not in current or
                                any(p in current.get(k, "").lower() for p in placeholders)]
                status = "ready" if not missing_keys else "incomplete"

            results.append({
                "mcp": mcp_dir.name,
                "category": cat,
                "status": status,
                "set": set_keys,
                "missing": missing_keys,
            })

    ready = [r for r in results if r["status"] == "ready"]
    incomplete = [r for r in results if r["status"] == "incomplete"]
    missing = [r for r in results if r["status"] == "missing"]

    return {
        "ok": True,
        "total_mcps": len(results),
        "ready": len(ready),
        "incomplete": len(incomplete),
        "missing_env": len(missing),
        "mcps": results,
        "summary": f"{len(ready)} ready, {len(incomplete)} incomplete, {len(missing)} missing .env",
    }


@mcp.tool()
def get_env(mcp_name: str, category: str) -> dict[str, Any]:
    """
    Read the current .env values for a specific MCP.
    Does not return secret values — shows keys and whether values are set.

    Args:
        mcp_name: e.g. "mcp-auth"
        category: e.g. "business"
    """
    mcp_dir = settings.ecosystem_root / category / mcp_name
    env_file = mcp_dir / ".env"
    env_example = mcp_dir / ".env.example"

    if not mcp_dir.exists():
        return {"ok": False, "error": f"MCP '{mcp_name}' not found at {mcp_dir}"}

    required = _read_env_example(env_example)
    current = _read_env_file(env_file)

    report = []
    for key in required:
        val = current.get(key, "")
        is_set = bool(val) and not any(p in val.lower() for p in ["your-", "change-this", "placeholder"])
        report.append({"key": key, "set": is_set,
                       "hint": val[:3] + "***" if is_set else "NOT SET"})

    return {"ok": True, "mcp": mcp_name, "category": category, "vars": report}


@mcp.tool()
def validate_env(mcp_name: str, category: str) -> dict[str, Any]:
    """
    Validate that all required env vars are set for an MCP.

    Args:
        mcp_name: e.g. "mcp-postgres"
        category: e.g. "data"
    """
    mcp_dir = settings.ecosystem_root / category / mcp_name
    env_example = mcp_dir / ".env.example"
    env_file = mcp_dir / ".env"

    if not mcp_dir.exists():
        return {"ok": False, "error": f"MCP '{mcp_name}' not found"}
    if not env_file.exists():
        return {"ok": False, "valid": False,
                "error": ".env file missing. Run setup.ps1 or copy .env.example to .env"}

    required = _read_env_example(env_example)
    current = _read_env_file(env_file)
    placeholders = ["your-", "change-this", "placeholder", "[password]", "[your-"]

    missing = [k for k in required if k not in current]
    unfilled = [k for k in required if k in current and
                any(p in current[k].lower() for p in placeholders)]

    valid = not missing and not unfilled
    return {
        "ok": True, "mcp": mcp_name, "valid": valid,
        "missing": missing, "unfilled": unfilled,
        "message": "All required vars are set." if valid else
                   f"{len(missing)} missing, {len(unfilled)} unfilled.",
    }


@mcp.tool()
def copy_var_to_mcp(
    key: str, source_mcp: str, source_category: str,
    target_mcp: str, target_category: str,
) -> dict[str, Any]:
    """
    Copy an env var value from one MCP's .env to another.

    Useful when multiple MCPs share the same DATABASE_URL or REDIS_URL.

    Args:
        key:              Variable name (e.g. "DATABASE_URL").
        source_mcp:       MCP to copy from.
        source_category:  Category of source MCP.
        target_mcp:       MCP to copy to.
        target_category:  Category of target MCP.
    """
    source_env = settings.ecosystem_root / source_category / source_mcp / ".env"
    target_env = settings.ecosystem_root / target_category / target_mcp / ".env"

    source_vars = _read_env_file(source_env)
    if key not in source_vars:
        return {"ok": False, "error": f"Key '{key}' not found in {source_mcp}/.env"}

    value = source_vars[key]
    target_vars = _read_env_file(target_env)
    target_vars[key] = value

    # Write back
    if target_env.exists():
        content = target_env.read_text(encoding="utf-8")
        if key in content:
            content = re.sub(rf"^{key}=.*$", f"{key}={value}", content, flags=re.MULTILINE)
        else:
            content += f"\n{key}={value}\n"
        target_env.write_text(content, encoding="utf-8")
    else:
        target_env.write_text(f"{key}={value}\n", encoding="utf-8")

    return {
        "ok": True, "key": key,
        "from": f"{source_category}/{source_mcp}",
        "to": f"{target_category}/{target_mcp}",
        "hint": value[:3] + "***",
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
