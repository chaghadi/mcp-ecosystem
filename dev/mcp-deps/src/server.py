"""server.py — mcp-deps MCP server entry point."""

import subprocess
from pathlib import Path
from typing import Any
from mcp.server.fastmcp import FastMCP
from src.config import settings

mcp = FastMCP(
    "mcp-deps",
    instructions="Dependency management MCP for mmiri28 solutions. Check outdated packages, update deps, run security audits across all MCPs.",
)


def _run(cmd: list[str], cwd: str, timeout: int = 60) -> dict[str, Any]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout)
        return {"ok": result.returncode == 0, "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip()}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Timed out after {timeout}s"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def check_outdated(mcp_name: str, category: str) -> dict[str, Any]:
    """
    Check for outdated dependencies in an MCP.

    Args:
        mcp_name: e.g. "mcp-auth"
        category: e.g. "business"
    """
    path = str(settings.ecosystem_root / category / mcp_name)
    if not Path(path).exists():
        return {"ok": False, "error": f"MCP '{mcp_name}' not found"}

    result = _run(["uv", "pip", "list", "--outdated", "--format=columns"], cwd=path)
    if not result["ok"]:
        # Try alternate approach
        result = _run(["uv", "tree", "--outdated"], cwd=path)

    lines = [l for l in result.get("stdout", "").splitlines() if l.strip()
             and not l.startswith("Package") and not l.startswith("---")]
    return {
        "ok": True, "mcp": mcp_name,
        "outdated_count": len(lines),
        "outdated": lines,
        "raw": result.get("stdout", ""),
    }


@mcp.tool()
def update_deps(mcp_name: str, category: str) -> dict[str, Any]:
    """
    Update all dependencies in an MCP to latest compatible versions.

    Args:
        mcp_name: e.g. "mcp-postgres"
        category: e.g. "data"
    """
    path = str(settings.ecosystem_root / category / mcp_name)
    if not Path(path).exists():
        return {"ok": False, "error": f"MCP '{mcp_name}' not found"}
    result = _run(["uv", "sync", "--upgrade"], cwd=path, timeout=120)
    return {"ok": result["ok"], "mcp": mcp_name,
            "output": result["stdout"] or result["stderr"]}


@mcp.tool()
def check_all_outdated() -> dict[str, Any]:
    """Check outdated dependencies across all MCPs."""
    root = settings.ecosystem_root
    categories = ["dev", "data", "business", "infra"]
    results = []
    total_outdated = 0

    for cat in categories:
        cat_path = root / cat
        if not cat_path.exists():
            continue
        for mcp_dir in sorted(cat_path.iterdir()):
            if not (mcp_dir / "pyproject.toml").exists():
                continue
            r = check_outdated(mcp_dir.name, cat)
            count = r.get("outdated_count", 0)
            total_outdated += count
            if count > 0:
                results.append({"mcp": mcp_dir.name, "category": cat,
                                 "outdated": count, "packages": r.get("outdated", [])})

    return {
        "ok": True,
        "total_outdated_packages": total_outdated,
        "mcps_with_outdated": len(results),
        "details": results,
        "summary": f"{total_outdated} outdated packages across {len(results)} MCPs",
    }


@mcp.tool()
def security_audit(mcp_name: str, category: str) -> dict[str, Any]:
    """
    Run a security audit on an MCP's dependencies.

    Uses pip-audit via uv.

    Args:
        mcp_name: e.g. "mcp-auth"
        category: e.g. "business"
    """
    path = str(settings.ecosystem_root / category / mcp_name)
    if not Path(path).exists():
        return {"ok": False, "error": f"MCP '{mcp_name}' not found"}

    result = _run(["uv", "run", "pip-audit", "--format=json"], cwd=path, timeout=120)
    if "pip-audit" in result.get("stderr", ""):
        # pip-audit not installed — add it and retry
        _run(["uv", "add", "--dev", "pip-audit"], cwd=path)
        result = _run(["uv", "run", "pip-audit", "--format=json"], cwd=path, timeout=120)

    return {
        "ok": result["ok"], "mcp": mcp_name,
        "vulnerabilities": result.get("stdout", "No vulnerabilities found."),
        "error": result.get("stderr", "") if not result["ok"] else None,
    }


@mcp.tool()
def list_deps(mcp_name: str, category: str) -> dict[str, Any]:
    """List all installed dependencies for an MCP."""
    path = str(settings.ecosystem_root / category / mcp_name)
    if not Path(path).exists():
        return {"ok": False, "error": f"MCP '{mcp_name}' not found"}
    result = _run(["uv", "pip", "list", "--format=columns"], cwd=path)
    return {"ok": result["ok"], "mcp": mcp_name, "deps": result.get("stdout", "")}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
