"""server.py — mcp-linter MCP server entry point."""

import subprocess
from pathlib import Path
from typing import Any
from mcp.server.fastmcp import FastMCP
from src.config import settings

mcp = FastMCP(
    "mcp-linter",
    instructions="Linter MCP for mmiri28 solutions. Ruff for Python (format + lint), ESLint for JS/TS. Auto-fix support.",
)


def _run(cmd: list[str], cwd: str) -> dict[str, Any]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=60)
        return {"ok": result.returncode == 0, "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(), "returncode": result.returncode}
    except FileNotFoundError as exc:
        return {"ok": False, "error": f"Tool not found: {exc}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Linter timed out"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def lint_python(path: str, fix: bool = False) -> dict[str, Any]:
    """
    Lint Python files with ruff.

    Args:
        path: Path to file or directory.
        fix:  Auto-fix fixable issues.
    """
    cmd = ["uv", "run", "ruff", "check", path]
    if fix:
        cmd.append("--fix")
    result = _run(cmd, cwd=str(settings.ecosystem_root))
    issues = len([l for l in result.get("stdout", "").splitlines() if ".py:" in l])
    return {
        "ok": result["ok"], "path": path,
        "issues": issues, "fixed": fix and result["ok"],
        "output": result["stdout"] or result["stderr"],
    }


@mcp.tool()
def format_python(path: str, check_only: bool = False) -> dict[str, Any]:
    """
    Format Python files with ruff format.

    Args:
        path:       Path to file or directory.
        check_only: Only check, don't write changes.
    """
    cmd = ["uv", "run", "ruff", "format", path]
    if check_only:
        cmd.append("--check")
    result = _run(cmd, cwd=str(settings.ecosystem_root))
    return {"ok": result["ok"], "path": path,
            "formatted": not check_only and result["ok"],
            "output": result["stdout"] or result["stderr"]}


@mcp.tool()
def lint_mcp(mcp_name: str, category: str, fix: bool = False) -> dict[str, Any]:
    """
    Lint all Python files in an MCP.

    Args:
        mcp_name: e.g. "mcp-auth"
        category: e.g. "business"
        fix:      Auto-fix issues.
    """
    mcp_path = str(settings.ecosystem_root / category / mcp_name / "src")
    return lint_python(mcp_path, fix=fix)


@mcp.tool()
def lint_all_mcps() -> dict[str, Any]:
    """Run ruff on all MCP source files in the ecosystem."""
    root = settings.ecosystem_root
    categories = ["dev", "data", "business", "infra"]
    results = []
    total_issues = 0

    for cat in categories:
        cat_path = root / cat
        if not cat_path.exists():
            continue
        for mcp_dir in sorted(cat_path.iterdir()):
            src = mcp_dir / "src"
            if not src.exists():
                continue
            result = lint_python(str(src))
            results.append({"mcp": mcp_dir.name, "category": cat,
                            "ok": result["ok"], "issues": result["issues"]})
            total_issues += result["issues"]

    return {
        "ok": total_issues == 0,
        "total_issues": total_issues,
        "mcps_checked": len(results),
        "with_issues": [r for r in results if r["issues"] > 0],
        "summary": f"{total_issues} issues across {len(results)} MCPs",
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
