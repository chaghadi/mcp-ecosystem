"""server.py — mcp-cloudflare MCP server entry point."""

import httpx
from typing import Any
from mcp.server.fastmcp import FastMCP
from src.config import settings

mcp = FastMCP(
    "mcp-cloudflare",
    instructions="Cloudflare MCP for mmiri28 solutions. Manage DNS records, purge cache, list R2 buckets. Companion to mcp-storage for object operations.",
)


def _get(path: str, params: dict | None = None) -> dict[str, Any]:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        r = httpx.get(f"{settings.base_url}{path}", headers=settings.headers,
                      params=params or {}, timeout=15)
        data = r.json()
        if data.get("success"):
            return {"ok": True, "data": data.get("result")}
        errors = data.get("errors", [])
        return {"ok": False, "error": errors[0].get("message") if errors else f"HTTP {r.status_code}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _post(path: str, body: dict) -> dict[str, Any]:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        r = httpx.post(f"{settings.base_url}{path}", headers=settings.headers,
                       json=body, timeout=15)
        data = r.json()
        if data.get("success"):
            return {"ok": True, "data": data.get("result")}
        errors = data.get("errors", [])
        return {"ok": False, "error": errors[0].get("message") if errors else f"HTTP {r.status_code}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _delete(path: str) -> dict[str, Any]:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        r = httpx.delete(f"{settings.base_url}{path}", headers=settings.headers, timeout=15)
        data = r.json()
        if data.get("success"):
            return {"ok": True, "data": data.get("result")}
        errors = data.get("errors", [])
        return {"ok": False, "error": errors[0].get("message") if errors else f"HTTP {r.status_code}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def health_check() -> dict:
    """Verify Cloudflare API token."""
    result = _get("/user/tokens/verify")
    if result["ok"]:
        return {"ok": True, "token_status": result["data"].get("status"),
                "account_id": settings.account_id or "not set"}
    return result


@mcp.tool()
def list_zones() -> dict:
    """List all domains (zones) under the Cloudflare account."""
    result = _get("/zones", {"per_page": 50})
    if result["ok"]:
        zones = [{"id": z["id"], "name": z["name"], "status": z["status"],
                  "plan": z.get("plan", {}).get("name")} for z in result["data"]]
        return {"ok": True, "count": len(zones), "zones": zones}
    return result


@mcp.tool()
def get_zone(domain: str) -> dict:
    """Get zone details for a specific domain."""
    result = _get(f"/zones", {"name": domain})
    if result["ok"] and result["data"]:
        z = result["data"][0]
        return {"ok": True, "zone_id": z["id"], "name": z["name"],
                "status": z["status"], "name_servers": z.get("name_servers", [])}
    return {"ok": False, "error": f"Zone '{domain}' not found."}


@mcp.tool()
def list_dns_records(zone_id: str) -> dict:
    """List all DNS records for a zone."""
    result = _get(f"/zones/{zone_id}/dns_records", {"per_page": 100})
    if result["ok"]:
        records = [{"id": r["id"], "type": r["type"], "name": r["name"],
                    "content": r["content"], "ttl": r["ttl"],
                    "proxied": r.get("proxied", False)} for r in result["data"]]
        return {"ok": True, "zone_id": zone_id, "count": len(records), "records": records}
    return result


@mcp.tool()
def create_dns_record(
    zone_id: str, type: str, name: str, content: str,
    ttl: int = 1, proxied: bool = False,
) -> dict:
    """
    Create a DNS record.

    Args:
        zone_id: Cloudflare zone ID.
        type:    Record type ("A", "AAAA", "CNAME", "TXT", "MX", etc.)
        name:    Record name (e.g. "www" or "@" for apex).
        content: Record value (IP for A, hostname for CNAME, etc.)
        ttl:     TTL in seconds. 1 = automatic.
        proxied: Route through Cloudflare proxy (only for A/AAAA/CNAME).
    """
    body = {"type": type, "name": name, "content": content,
            "ttl": ttl, "proxied": proxied}
    result = _post(f"/zones/{zone_id}/dns_records", body)
    if result["ok"]:
        r = result["data"]
        return {"ok": True, "record_id": r["id"], "name": r["name"],
                "type": r["type"], "content": r["content"]}
    return result


@mcp.tool()
def update_dns_record(
    zone_id: str, record_id: str,
    type: str | None = None, name: str | None = None,
    content: str | None = None, ttl: int | None = None,
    proxied: bool | None = None,
) -> dict:
    """Update an existing DNS record."""
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    body = {k: v for k, v in {
        "type": type, "name": name, "content": content,
        "ttl": ttl, "proxied": proxied
    }.items() if v is not None}
    try:
        r = httpx.patch(f"{settings.base_url}/zones/{zone_id}/dns_records/{record_id}",
                        headers=settings.headers, json=body, timeout=15)
        data = r.json()
        if data.get("success"):
            return {"ok": True, "record_id": record_id}
        return {"ok": False, "error": data.get("errors", [{}])[0].get("message")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def delete_dns_record(zone_id: str, record_id: str) -> dict:
    """Delete a DNS record."""
    return _delete(f"/zones/{zone_id}/dns_records/{record_id}")


@mcp.tool()
def purge_cache(zone_id: str, urls: list[str] | None = None) -> dict:
    """
    Purge Cloudflare cache.

    Args:
        zone_id: Zone to purge.
        urls:    Specific URLs to purge. If None, purges everything.
    """
    body = {"files": urls} if urls else {"purge_everything": True}
    result = _post(f"/zones/{zone_id}/purge_cache", body)
    if result["ok"]:
        return {"ok": True, "purged": "specific URLs" if urls else "all cache",
                "count": len(urls) if urls else None}
    return result


@mcp.tool()
def list_r2_buckets() -> dict:
    """List R2 buckets in the Cloudflare account."""
    if not settings.account_id:
        return {"ok": False, "error": "CLOUDFLARE_ACCOUNT_ID not set."}
    result = _get(f"/accounts/{settings.account_id}/r2/buckets")
    if result["ok"]:
        buckets = result["data"].get("buckets", []) if isinstance(result["data"], dict) else result["data"]
        return {"ok": True, "count": len(buckets),
                "buckets": [{"name": b.get("name"), "created": b.get("creation_date")} for b in buckets]}
    return result


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
