"""server.py — mcp-docker-ops MCP server entry point.

Wraps the docker CLI for building, pushing, and managing containers.
Images are pushed to ghcr.io/chaghadi/ per ADR-0004.
"""

import subprocess
from typing import Any
from mcp.server.fastmcp import FastMCP
from src.config import settings

mcp = FastMCP(
    "mcp-docker-ops",
    instructions="Docker operations MCP for mmiri28 solutions. Build and push to ghcr.io/chaghadi. Run, stop, and inspect containers.",
)

REGISTRY = "ghcr.io"


def _run(cmd: list[str], cwd: str | None = None, timeout: int = 300) -> dict[str, Any]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout)
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Command timed out after {timeout}s"}
    except FileNotFoundError:
        return {"ok": False, "error": "docker not found. Is Docker Desktop running?"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def health_check() -> dict:
    """Check docker is running and return version info."""
    result = _run(["docker", "version", "--format", "{{.Server.Version}}"])
    if result["ok"]:
        return {"ok": True, "docker_version": result["stdout"],
                "registry": f"{REGISTRY}/{settings.github_owner}"}
    return {"ok": False, "error": "Docker is not running. Start Docker Desktop."}


@mcp.tool()
def build_image(
    mcp_name: str,
    category: str,
    tag: str = "latest",
    no_cache: bool = False,
) -> dict[str, Any]:
    """
    Build a Docker image for an MCP.

    Image is tagged as ghcr.io/chaghadi/{mcp_name}:{tag}.

    Args:
        mcp_name: e.g. "mcp-postgres"
        category: e.g. "data"
        tag:      Image tag. Default: "latest".
        no_cache: Force rebuild from scratch.
    """
    context = str(settings.ecosystem_root / category / mcp_name)
    image = f"{REGISTRY}/{settings.github_owner}/{mcp_name}:{tag}"
    cmd = ["docker", "build", "-t", image, context]
    if no_cache:
        cmd.append("--no-cache")
    result = _run(cmd, timeout=600)
    if result["ok"]:
        return {"ok": True, "image": image, "output": result["stdout"][-500:]}
    return {"ok": False, "error": result["stderr"][-500:] or result["stdout"][-500:]}


@mcp.tool()
def push_image(mcp_name: str, tag: str = "latest") -> dict[str, Any]:
    """
    Push a built image to ghcr.io/chaghadi.
    Must be logged in: docker login ghcr.io -u chaghadi

    Args:
        mcp_name: e.g. "mcp-postgres"
        tag:      Image tag.
    """
    image = f"{REGISTRY}/{settings.github_owner}/{mcp_name}:{tag}"
    result = _run(["docker", "push", image], timeout=300)
    if result["ok"]:
        return {"ok": True, "image": image, "pushed": True}
    return {"ok": False, "error": result["stderr"] or result["stdout"]}


@mcp.tool()
def list_images(filter_name: str = "ghcr.io/chaghadi") -> dict[str, Any]:
    """List Docker images, optionally filtered by name."""
    result = _run(["docker", "images", "--format",
                   "{{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}", filter_name])
    if result["ok"]:
        images = []
        for line in result["stdout"].splitlines():
            if line.strip():
                parts = line.split("\t")
                images.append({"image": parts[0], "size": parts[1] if len(parts) > 1 else "",
                               "created": parts[2] if len(parts) > 2 else ""})
        return {"ok": True, "count": len(images), "images": images}
    return {"ok": False, "error": result["stderr"]}


@mcp.tool()
def list_containers(all_containers: bool = False) -> dict[str, Any]:
    """List running (or all) Docker containers."""
    cmd = ["docker", "ps", "--format",
           "{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"]
    if all_containers:
        cmd.append("-a")
    result = _run(cmd)
    if result["ok"]:
        containers = []
        for line in result["stdout"].splitlines():
            if line.strip():
                parts = line.split("\t")
                containers.append({
                    "id": parts[0], "name": parts[1] if len(parts) > 1 else "",
                    "image": parts[2] if len(parts) > 2 else "",
                    "status": parts[3] if len(parts) > 3 else "",
                    "ports": parts[4] if len(parts) > 4 else "",
                })
        return {"ok": True, "count": len(containers), "containers": containers}
    return {"ok": False, "error": result["stderr"]}


@mcp.tool()
def get_logs(container: str, lines: int = 50) -> dict[str, Any]:
    """Get recent logs from a container."""
    result = _run(["docker", "logs", "--tail", str(lines), container])
    return {"ok": result["ok"], "container": container,
            "logs": result["stdout"] or result["stderr"]}


@mcp.tool()
def stop_container(container: str) -> dict[str, Any]:
    """Stop a running container."""
    result = _run(["docker", "stop", container])
    return {"ok": result["ok"], "container": container,
            "message": "Stopped." if result["ok"] else result["stderr"]}


@mcp.tool()
def run_compose(
    action: str = "up",
    detach: bool = True,
) -> dict[str, Any]:
    """
    Run docker-compose.mcps.yml in the ecosystem root.

    Args:
        action: "up", "down", "ps", "logs"
        detach: Run in background (only for 'up'). Default: True.
    """
    compose_file = str(settings.ecosystem_root / "docker-compose.mcps.yml")
    cmd = ["docker", "compose", "-f", compose_file, action]
    if action == "up" and detach:
        cmd.append("-d")
    result = _run(cmd, cwd=str(settings.ecosystem_root), timeout=120)
    return {"ok": result["ok"], "action": action,
            "output": result["stdout"] or result["stderr"]}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
