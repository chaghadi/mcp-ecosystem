"""server.py — mcp-git-ops MCP server entry point."""

from mcp.server.fastmcp import FastMCP
from src.config import settings
from src.tools.git_tools import (
    run_create_repo, run_get_repo, run_list_repos,
    run_create_branch, run_create_pr, run_list_prs, run_create_issue,
)

mcp = FastMCP(
    "mcp-git-ops",
    instructions="GitHub operations MCP for mmiri28 solutions. Create repos, branches, PRs, issues. All under the chaghadi account.",
)


@mcp.tool()
def health_check() -> dict:
    """Verify GitHub token and return authenticated user info."""
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    import httpx
    try:
        r = httpx.get("https://api.github.com/user", headers=settings.headers, timeout=5)
        d = r.json()
        return {"ok": True, "login": d.get("login"), "name": d.get("name"),
                "public_repos": d.get("public_repos")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def create_repo(name: str, description: str = "", private: bool = True) -> dict:
    """Create a new GitHub repository. Default: private."""
    return run_create_repo(name=name, description=description, private=private)


@mcp.tool()
def get_repo(repo: str) -> dict:
    """Get info about a repository."""
    return run_get_repo(repo=repo)


@mcp.tool()
def list_repos(page: int = 1, limit: int = 30) -> dict:
    """List repositories for the configured owner."""
    return run_list_repos(page=page, limit=limit)


@mcp.tool()
def create_branch(repo: str, branch_name: str, from_branch: str = "main") -> dict:
    """Create a new branch in a repository."""
    return run_create_branch(repo=repo, branch_name=branch_name, from_branch=from_branch)


@mcp.tool()
def create_pr(repo: str, title: str, body: str, head: str, base: str = "main") -> dict:
    """
    Create a pull request.

    Args:
        repo:  Repository name.
        title: PR title.
        body:  PR description.
        head:  Source branch.
        base:  Target branch (default: main).
    """
    return run_create_pr(repo=repo, title=title, body=body, head=head, base=base)


@mcp.tool()
def list_prs(repo: str, state: str = "open") -> dict:
    """List pull requests. state: 'open' | 'closed' | 'all'"""
    return run_list_prs(repo=repo, state=state)


@mcp.tool()
def create_issue(repo: str, title: str, body: str = "", labels: list[str] | None = None) -> dict:
    """Create a GitHub issue."""
    return run_create_issue(repo=repo, title=title, body=body, labels=labels)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
