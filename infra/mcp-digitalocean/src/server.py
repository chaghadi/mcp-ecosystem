"""server.py — mcp-digitalocean MCP server entry point."""

import httpx
from mcp.server.fastmcp import FastMCP
from src.config import settings

mcp = FastMCP(
    "mcp-digitalocean",
    instructions="DigitalOcean infrastructure MCP for mmiri28 solutions. Manage apps, databases, droplets, and domains.",
)


def _get(path: str, params: dict = {}) -> dict:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        r = httpx.get(f"{settings.base_url}{path}", headers=settings.headers, params=params, timeout=15)
        if r.status_code == 200:
            return {"ok": True, "data": r.json()}
        return {"ok": False, "error": r.json().get("message", f"HTTP {r.status_code}")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _post(path: str, body: dict) -> dict:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        r = httpx.post(f"{settings.base_url}{path}", headers=settings.headers, json=body, timeout=15)
        if r.status_code in (200, 201, 202):
            return {"ok": True, "data": r.json()}
        return {"ok": False, "error": r.json().get("message", f"HTTP {r.status_code}")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def health_check() -> dict:
    """Verify DigitalOcean API token."""
    result = _get("/account")
    if result["ok"]:
        acc = result["data"].get("account", {})
        return {"ok": True, "email": acc.get("email"), "status": acc.get("status"),
                "droplet_limit": acc.get("droplet_limit")}
    return result


@mcp.tool()
def list_apps() -> dict:
    """List all App Platform apps."""
    result = _get("/apps")
    if result["ok"]:
        apps = [{"id": a["id"], "spec_name": a["spec"]["name"],
                 "phase": a.get("phase"), "live_url": a.get("live_url"),
                 "updated_at": a.get("updated_at")}
                for a in result["data"].get("apps", [])]
        return {"ok": True, "count": len(apps), "apps": apps}
    return result


@mcp.tool()
def get_app(app_id: str) -> dict:
    """Get details of a DO App Platform app."""
    return _get(f"/apps/{app_id}")


@mcp.tool()
def create_app(spec: dict) -> dict:
    """
    Create a new App Platform app from a spec dict.

    The spec follows DigitalOcean App Platform spec format.
    Use get_app to see an existing app spec for reference.
    """
    return _post("/apps", {"spec": spec})


@mcp.tool()
def list_databases() -> dict:
    """List all managed databases."""
    result = _get("/databases")
    if result["ok"]:
        dbs = [{"id": d["id"], "name": d["name"], "engine": d["engine"],
                "status": d["status"], "region": d["region"],
                "size": d.get("size_slug")}
               for d in result["data"].get("databases", [])]
        return {"ok": True, "count": len(dbs), "databases": dbs}
    return result


@mcp.tool()
def get_database_connection(database_id: str) -> dict:
    """Get connection details for a managed database."""
    result = _get(f"/databases/{database_id}")
    if result["ok"]:
        db = result["data"].get("database", {})
        conn = db.get("connection", {})
        return {"ok": True, "name": db.get("name"), "engine": db.get("engine"),
                "host": conn.get("host"), "port": conn.get("port"),
                "database": conn.get("database"), "ssl": conn.get("ssl")}
    return result


@mcp.tool()
def list_domains() -> dict:
    """List all domains registered in DigitalOcean."""
    result = _get("/domains")
    if result["ok"]:
        domains = [{"name": d["name"], "ttl": d.get("ttl")}
                   for d in result["data"].get("domains", [])]
        return {"ok": True, "count": len(domains), "domains": domains}
    return result


@mcp.tool()
def list_droplets() -> dict:
    """List all Droplets."""
    result = _get("/droplets")
    if result["ok"]:
        droplets = [{"id": d["id"], "name": d["name"], "status": d["status"],
                     "region": d["region"]["slug"], "size": d["size_slug"],
                     "ip": d["networks"]["v4"][0]["ip_address"] if d["networks"]["v4"] else None}
                    for d in result["data"].get("droplets", [])]
        return {"ok": True, "count": len(droplets), "droplets": droplets}
    return result


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
