"""server.py — mcp-test-runner MCP server entry point."""

import subprocess
import json
from pathlib import Path
from typing import Any
from mcp.server.fastmcp import FastMCP
from src.config import settings

mcp = FastMCP(
    "mcp-test-runner",
    instructions="Test runner MCP for mmiri28 solutions. Run pytest across all MCPs or specific ones. Parse results and report failures.",
)


def _run_pytest(path: str, verbose: bool = False) -> dict[str, Any]:
    cmd = ["uv", "run", "pytest", "tests/", "-q", "--tb=short", "--no-header"]
    if verbose:
        cmd[4] = "-v"
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=path, timeout=120)
        output = result.stdout + result.stderr
        # Parse summary line
        passed = failed = errors = skipped = 0
        for line in output.splitlines():
            if "passed" in line or "failed" in line or "error" in line:
                import re
                nums = re.findall(r"(\d+) (passed|failed|error|skipped)", line)
                for count, kind in nums:
                    if kind == "passed":   passed = int(count)
                    elif kind == "failed": failed = int(count)
                    elif kind == "error":  errors = int(count)
                    elif kind == "skipped": skipped = int(count)
        return {
            "ok": result.returncode == 0,
            "passed": passed, "failed": failed,
            "errors": errors, "skipped": skipped,
            "output": output[-2000:],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Tests timed out after 120s"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def run_mcp_tests(mcp_name: str, category: str, verbose: bool = False) -> dict[str, Any]:
    """
    Run tests for a specific MCP.

    Args:
        mcp_name: e.g. "mcp-auth"
        category: e.g. "business"
        verbose:  Show full test names.
    """
    path = str(settings.ecosystem_root / category / mcp_name)
    if not Path(path).exists():
        return {"ok": False, "error": f"MCP '{mcp_name}' not found at {path}"}
    result = _run_pytest(path, verbose)
    result["mcp"] = mcp_name
    result["category"] = category
    return result


@mcp.tool()
def run_all_mcp_tests(stop_on_failure: bool = False) -> dict[str, Any]:
    """
    Run tests across all MCPs in the ecosystem.

    Args:
        stop_on_failure: Stop after the first failing MCP.
    """
    root = settings.ecosystem_root
    categories = ["dev", "data", "business", "infra"]
    results = []
    total_passed = total_failed = 0

    for cat in categories:
        cat_path = root / cat
        if not cat_path.exists():
            continue
        for mcp_dir in sorted(cat_path.iterdir()):
            if not mcp_dir.is_dir() or not (mcp_dir / "tests").exists():
                continue
            result = _run_pytest(str(mcp_dir))
            result["mcp"] = mcp_dir.name
            result["category"] = cat
            results.append(result)
            total_passed += result.get("passed", 0)
            total_failed += result.get("failed", 0) + result.get("errors", 0)
            if stop_on_failure and total_failed > 0:
                break

    failures = [r for r in results if not r["ok"]]
    return {
        "ok": total_failed == 0,
        "total_passed": total_passed,
        "total_failed": total_failed,
        "mcps_tested": len(results),
        "failures": [{"mcp": f["mcp"], "failed": f.get("failed", 0),
                      "output": f.get("output", "")[-500:]} for f in failures],
        "summary": f"{total_passed} passed, {total_failed} failed across {len(results)} MCPs",
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
