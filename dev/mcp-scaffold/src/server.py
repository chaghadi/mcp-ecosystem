"""server.py — mcp-scaffold MCP server entry point.

Generates new app repositories with proper structure, wired to the MCP ecosystem.
Each app gets its own repo under github.com/chaghadi/app-{name}.
"""

import json
import base64
import httpx
from mcp.server.fastmcp import FastMCP
from src.config import settings

mcp = FastMCP(
    "mcp-scaffold",
    instructions="App scaffold MCP for mmiri28 solutions. Generates new app repos wired to the MCP ecosystem. Creates React/Vite, FastAPI, and mobile app structures.",
)

GH_API = "https://api.github.com"


def _gh_headers():
    return {"Authorization": f"Bearer {settings.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"}


def _create_file(repo: str, path: str, content: str, message: str) -> bool:
    """Create a file in a GitHub repo via the API."""
    encoded = base64.b64encode(content.encode()).decode()
    r = httpx.put(
        f"{GH_API}/repos/{settings.github_owner}/{repo}/contents/{path}",
        headers=_gh_headers(),
        json={"message": message, "content": encoded},
        timeout=15,
    )
    return r.status_code in (200, 201)


def _scaffold_vscode_mcp_json(mcps: list[str]) -> str:
    """Generate .vscode/mcp.json that references the shared mcp-ecosystem."""
    servers = {}
    mcp_paths = {
        "mcp-auth": "business/mcp-auth",
        "mcp-user-mgmt": "business/mcp-user-mgmt",
        "mcp-billing": "business/mcp-billing",
        "mcp-notifications": "business/mcp-notifications",
        "mcp-analytics": "business/mcp-analytics",
        "mcp-storage": "data/mcp-storage",
        "mcp-postgres": "data/mcp-postgres",
        "mcp-redis": "data/mcp-redis",
        "mcp-search": "data/mcp-search",
        "mcp-webhooks": "business/mcp-webhooks",
    }
    for mcp in mcps:
        if mcp in mcp_paths:
            servers[mcp] = {
                "type": "stdio", "command": "uv", "args": ["run", mcp],
                "cwd": f"../mcp-ecosystem/{mcp_paths[mcp]}"
            }
    return json.dumps({"servers": servers}, indent=2)


@mcp.tool()
def health_check() -> dict:
    """Verify scaffold credentials."""
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    return {"ok": True, "owner": settings.github_owner, "brand": settings.brand}


@mcp.tool()
def scaffold_web_app(
    name: str,
    description: str = "",
    mcps: list[str] | None = None,
) -> dict:
    """
    Generate a new React/Vite web app repo.

    Creates github.com/chaghadi/app-{name} with:
    - Vite + React + TypeScript setup
    - .vscode/mcp.json wired to the shared mcp-ecosystem
    - README, .gitignore, package.json

    Args:
        name:        App name (e.g. "marketplace"). Repo: app-{name}.
        description: Short description.
        mcps:        MCP servers this app needs (e.g. ["mcp-auth", "mcp-billing"]).
    """
    err = settings.validate()
    if err: return {"ok": False, "error": err}

    repo_name = f"app-{name}"
    default_mcps = mcps or ["mcp-auth", "mcp-analytics"]

    # Create repo
    r = httpx.post(f"{GH_API}/user/repos", headers=_gh_headers(),
                   json={"name": repo_name, "description": description,
                         "private": True, "auto_init": False}, timeout=10)
    if r.status_code not in (200, 201):
        return {"ok": False, "error": r.json().get("message", "Failed to create repo")}

    repo_data = r.json()
    files_created = []

    file_contents = {
        "README.md": f"# {name}\n\n{description}\n\n**Brand:** {settings.brand}\n\n## Setup\n\n```bash\nnpm install\nnpm run dev\n```\n\n## MCP ecosystem\n\nThis app uses the shared mcp-ecosystem. See `.vscode/mcp.json`.\n",
        ".gitignore": "node_modules/\ndist/\n.env\n.env.local\n*.log\n",
        "package.json": json.dumps({
            "name": name, "version": "0.1.0", "private": True,
            "scripts": {"dev": "vite", "build": "vite build", "preview": "vite preview"},
            "dependencies": {"react": "^18.2.0", "react-dom": "^18.2.0"},
            "devDependencies": {"@vitejs/plugin-react": "^4.0.0", "typescript": "^5.0.0", "vite": "^5.0.0"},
        }, indent=2),
        ".vscode/mcp.json": _scaffold_vscode_mcp_json(default_mcps),
        ".env.example": "# Add your environment variables here\nVITE_API_URL=http://localhost:8000\n",
        "src/main.tsx": f'import React from "react"\nimport ReactDOM from "react-dom/client"\nimport App from "./App"\n\nReactDOM.createRoot(document.getElementById("root")!).render(\n  <React.StrictMode><App /></React.StrictMode>\n)\n',
        "src/App.tsx": f'export default function App() {{\n  return <div><h1>{name}</h1><p>{settings.brand}</p></div>\n}}\n',
        "index.html": f'<!DOCTYPE html>\n<html>\n<head><title>{name}</title></head>\n<body><div id="root"></div><script type="module" src="/src/main.tsx"></script></body>\n</html>\n',
        "vite.config.ts": 'import { defineConfig } from "vite"\nimport react from "@vitejs/plugin-react"\nexport default defineConfig({ plugins: [react()] })\n',
    }

    for path, content in file_contents.items():
        if _create_file(repo_name, path, content, f"feat: initial scaffold — {path}"):
            files_created.append(path)

    return {
        "ok": True, "repo": repo_data["full_name"],
        "url": repo_data["html_url"], "clone_url": repo_data["clone_url"],
        "files_created": files_created, "mcps_wired": default_mcps,
        "next_steps": [
            f"git clone {repo_data['clone_url']}",
            f"cd {repo_name} && npm install && npm run dev",
            "Copy .env.example to .env and add your values",
        ],
    }


@mcp.tool()
def scaffold_api(
    name: str,
    description: str = "",
    mcps: list[str] | None = None,
) -> dict:
    """
    Generate a new FastAPI backend repo.

    Creates github.com/chaghadi/app-{name}-api with:
    - FastAPI + uvicorn setup
    - .vscode/mcp.json wired to mcp-ecosystem
    - pyproject.toml, README, .gitignore

    Args:
        name:        App name (e.g. "marketplace"). Repo: app-{name}-api.
        description: Short description.
        mcps:        MCP servers this API needs.
    """
    err = settings.validate()
    if err: return {"ok": False, "error": err}

    repo_name = f"app-{name}-api"
    default_mcps = mcps or ["mcp-auth", "mcp-postgres", "mcp-analytics"]

    r = httpx.post(f"{GH_API}/user/repos", headers=_gh_headers(),
                   json={"name": repo_name, "description": description,
                         "private": True, "auto_init": False}, timeout=10)
    if r.status_code not in (200, 201):
        return {"ok": False, "error": r.json().get("message", "Failed to create repo")}

    repo_data = r.json()
    files_created = []

    file_contents = {
        "README.md": f"# {name} API\n\n{description}\n\n**Brand:** {settings.brand}\n\n## Setup\n\n```bash\nuv sync\nuv run uvicorn src.main:app --reload\n```\n",
        ".gitignore": "__pycache__/\n.venv/\n.env\n*.pyc\ndist/\n",
        "pyproject.toml": f'[project]\nname = "{name}-api"\nversion = "0.1.0"\nrequires-python = ">=3.11"\ndependencies = [\n    "fastapi>=0.110.0",\n    "uvicorn[standard]>=0.27.0",\n    "python-dotenv>=1.0.0",\n]\n\n[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n',
        ".vscode/mcp.json": _scaffold_vscode_mcp_json(default_mcps),
        ".env.example": "DATABASE_URL=\nREDIS_URL=\nJWT_SECRET=\n",
        "src/__init__.py": "",
        "src/main.py": f'from fastapi import FastAPI\nfrom fastapi.middleware.cors import CORSMiddleware\n\napp = FastAPI(title="{name} API", version="0.1.0")\n\napp.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])\n\n@app.get("/health")\ndef health():\n    return {{"ok": True, "service": "{name}-api"}}\n',
    }

    for path, content in file_contents.items():
        if _create_file(repo_name, path, content, f"feat: initial scaffold — {path}"):
            files_created.append(path)

    return {
        "ok": True, "repo": repo_data["full_name"],
        "url": repo_data["html_url"], "clone_url": repo_data["clone_url"],
        "files_created": files_created, "mcps_wired": default_mcps,
    }


@mcp.tool()
def list_app_repos() -> dict:
    """List all app-* repos under the configured owner."""
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        r = httpx.get(f"{GH_API}/users/{settings.github_owner}/repos",
                      headers=_gh_headers(), params={"per_page": 100, "sort": "updated"}, timeout=10)
        all_repos = r.json()
        app_repos = [{"name": repo["name"], "url": repo["html_url"],
                      "description": repo.get("description"), "private": repo["private"]}
                     for repo in all_repos if repo["name"].startswith("app-")]
        return {"ok": True, "count": len(app_repos), "repos": app_repos}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
