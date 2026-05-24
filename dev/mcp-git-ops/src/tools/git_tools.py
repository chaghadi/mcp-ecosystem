"""git_tools.py — GitHub API operations."""

from typing import Any
import httpx
from src.config import settings


def _get(path: str) -> dict[str, Any]:
    try:
        r = httpx.get(f"{settings.base_url}{path}", headers=settings.headers, timeout=10)
        if r.status_code == 200:
            return {"ok": True, "data": r.json()}
        return {"ok": False, "error": r.json().get("message", f"HTTP {r.status_code}")}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _post(path: str, body: dict) -> dict[str, Any]:
    try:
        r = httpx.post(f"{settings.base_url}{path}", headers=settings.headers, json=body, timeout=10)
        if r.status_code in (200, 201):
            return {"ok": True, "data": r.json()}
        return {"ok": False, "error": r.json().get("message", f"HTTP {r.status_code}")}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _patch(path: str, body: dict) -> dict[str, Any]:
    try:
        r = httpx.patch(f"{settings.base_url}{path}", headers=settings.headers, json=body, timeout=10)
        if r.status_code in (200, 201):
            return {"ok": True, "data": r.json()}
        return {"ok": False, "error": r.json().get("message", f"HTTP {r.status_code}")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def run_create_repo(name: str, description: str = "", private: bool = True) -> dict[str, Any]:
    """Create a new GitHub repo under the configured owner."""
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    result = _post("/user/repos", {"name": name, "description": description,
                                    "private": private, "auto_init": True})
    if result["ok"]:
        d = result["data"]
        return {"ok": True, "repo": d["full_name"], "url": d["html_url"],
                "clone_url": d["clone_url"], "default_branch": d["default_branch"]}
    return result


def run_get_repo(repo: str) -> dict[str, Any]:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    result = _get(f"/repos/{settings.github_owner}/{repo}")
    if result["ok"]:
        d = result["data"]
        return {"ok": True, "repo": d["full_name"], "description": d.get("description"),
                "default_branch": d["default_branch"], "url": d["html_url"],
                "stars": d["stargazers_count"], "private": d["private"]}
    return result


def run_list_repos(page: int = 1, limit: int = 30) -> dict[str, Any]:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    result = _get(f"/users/{settings.github_owner}/repos?per_page={min(limit,100)}&page={page}&sort=updated")
    if result["ok"]:
        repos = [{"name": r["name"], "description": r.get("description"), 
                  "private": r["private"], "url": r["html_url"],
                  "updated_at": r["updated_at"]} for r in result["data"]]
        return {"ok": True, "repos": repos, "count": len(repos)}
    return result


def run_create_branch(repo: str, branch_name: str, from_branch: str = "main") -> dict[str, Any]:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    # Get SHA of the source branch
    sha_result = _get(f"/repos/{settings.github_owner}/{repo}/git/ref/heads/{from_branch}")
    if not sha_result["ok"]:
        return sha_result
    sha = sha_result["data"]["object"]["sha"]
    result = _post(f"/repos/{settings.github_owner}/{repo}/git/refs",
                   {"ref": f"refs/heads/{branch_name}", "sha": sha})
    if result["ok"]:
        return {"ok": True, "repo": repo, "branch": branch_name,
                "from": from_branch, "sha": sha}
    return result


def run_create_pr(repo: str, title: str, body: str,
                  head: str, base: str = "main") -> dict[str, Any]:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    result = _post(f"/repos/{settings.github_owner}/{repo}/pulls",
                   {"title": title, "body": body, "head": head, "base": base})
    if result["ok"]:
        d = result["data"]
        return {"ok": True, "pr_number": d["number"], "url": d["html_url"],
                "title": title, "state": d["state"]}
    return result


def run_list_prs(repo: str, state: str = "open") -> dict[str, Any]:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    result = _get(f"/repos/{settings.github_owner}/{repo}/pulls?state={state}&per_page=50")
    if result["ok"]:
        prs = [{"number": p["number"], "title": p["title"], "state": p["state"],
                "url": p["html_url"], "author": p["user"]["login"],
                "created_at": p["created_at"]} for p in result["data"]]
        return {"ok": True, "repo": repo, "prs": prs, "count": len(prs)}
    return result


def run_create_issue(repo: str, title: str, body: str = "",
                     labels: list[str] | None = None) -> dict[str, Any]:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    payload: dict = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels
    result = _post(f"/repos/{settings.github_owner}/{repo}/issues", payload)
    if result["ok"]:
        d = result["data"]
        return {"ok": True, "issue_number": d["number"], "url": d["html_url"],
                "title": title}
    return result
