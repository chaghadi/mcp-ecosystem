"""server.py — mcp-vercel MCP server entry point."""

import httpx
from mcp.server.fastmcp import FastMCP
from src.config import settings

mcp = FastMCP(
    "mcp-vercel",
    instructions="Vercel deployment MCP for mmiri28 solutions. Deploy projects, manage env vars, check deployment status.",
)


def _get(path: str, params: dict = {}) -> dict:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        r = httpx.get(f"{settings.base_url}{path}", headers=settings.headers, params=params, timeout=15)
        if r.status_code == 200:
            return {"ok": True, "data": r.json()}
        return {"ok": False, "error": r.json().get("error", {}).get("message", f"HTTP {r.status_code}")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _post(path: str, body: dict) -> dict:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        r = httpx.post(f"{settings.base_url}{path}", headers=settings.headers, json=body, timeout=15)
        if r.status_code in (200, 201):
            return {"ok": True, "data": r.json()}
        return {"ok": False, "error": r.json().get("error", {}).get("message", f"HTTP {r.status_code}")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def health_check() -> dict:
    """Verify Vercel token."""
    result = _get("/v2/user")
    if result["ok"]:
        u = result["data"].get("user", {})
        return {"ok": True, "username": u.get("username"), "email": u.get("email")}
    return result


@mcp.tool()
def list_projects() -> dict:
    """List all Vercel projects."""
    result = _get("/v9/projects", {"limit": 100})
    if result["ok"]:
        projects = [{"id": p["id"], "name": p["name"], "framework": p.get("framework"),
                     "url": f"https://{p['name']}.vercel.app"} for p in result["data"].get("projects", [])]
        return {"ok": True, "count": len(projects), "projects": projects}
    return result


@mcp.tool()
def get_project(project_name: str) -> dict:
    """Get details for a Vercel project."""
    return _get(f"/v9/projects/{project_name}")


@mcp.tool()
def list_deployments(project_name: str, limit: int = 10) -> dict:
    """List recent deployments for a project."""
    result = _get("/v6/deployments", {"app": project_name, "limit": min(limit, 100)})
    if result["ok"]:
        deps = [{"uid": d["uid"], "url": d.get("url"), "state": d.get("state"),
                 "created_at": d.get("createdAt"), "branch": d.get("meta", {}).get("githubCommitRef")}
                for d in result["data"].get("deployments", [])]
        return {"ok": True, "project": project_name, "deployments": deps}
    return result


@mcp.tool()
def get_deployment(deployment_id: str) -> dict:
    """Get status of a specific deployment."""
    return _get(f"/v13/deployments/{deployment_id}")


@mcp.tool()
def set_env_var(
    project_name: str, key: str, value: str,
    target: list[str] | None = None,
) -> dict:
    """
    Set an environment variable on a Vercel project.

    Args:
        project_name: The project slug.
        key:          Variable name (e.g. "DATABASE_URL").
        value:        Variable value.
        target:       Environments: ["production", "preview", "development"]. Default: all.
    """
    result = _post(f"/v9/projects/{project_name}/env", {
        "key": key, "value": value,
        "type": "encrypted",
        "target": target or ["production", "preview", "development"],
    })
    if result["ok"]:
        return {"ok": True, "project": project_name, "key": key, "target": target or "all"}
    return result


@mcp.tool()
def create_project(
    name: str, framework: str = "nextjs",
    git_repo: str | None = None,
) -> dict:
    """
    Create a new Vercel project.

    Args:
        name:      Project name (becomes name.vercel.app).
        framework: Framework preset (nextjs, vite, create-react-app, etc.)
        git_repo:  GitHub repo to link (format: "owner/repo").
    """
    body: dict = {"name": name, "framework": framework}
    if git_repo:
        body["gitRepository"] = {"type": "github", "repo": git_repo}
    return _post("/v9/projects", body)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
