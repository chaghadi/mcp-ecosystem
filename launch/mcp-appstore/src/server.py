"""server.py — mcp-appstore MCP server entry point.

App Store Connect API — manage iOS apps.
JWT auth with ES256 signing using your .p8 private key.

Setup:
1. App Store Connect → Users and Access → Keys → Create new key
2. Download the .p8 file (you only get one chance)
3. Set APPSTORE_KEY_ID, APPSTORE_ISSUER_ID, APPSTORE_PRIVATE_KEY_PATH
"""

import time
from typing import Any

import httpx
import jwt as pyjwt

from mcp.server.fastmcp import FastMCP
from src.config import settings

mcp = FastMCP(
    "mcp-appstore",
    instructions="App Store Connect MCP for mmiri28 solutions. Manage iOS app metadata, fetch reviews, list TestFlight builds.",
)


def _generate_token() -> str:
    """Generate a JWT for App Store Connect API."""
    err = settings.validate()
    if err: raise RuntimeError(err)
    now = int(time.time())
    payload = {
        "iss": settings.issuer_id,
        "exp": now + 1200,  # 20 min max
        "aud": "appstoreconnect-v1",
    }
    return pyjwt.encode(
        payload, settings.get_private_key(), algorithm="ES256",
        headers={"kid": settings.key_id},
    )


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_generate_token()}"}


def _get(path: str, params: dict | None = None) -> dict[str, Any]:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        r = httpx.get(f"{settings.base_url}{path}",
                      headers=_headers(), params=params or {}, timeout=15)
        if r.status_code == 200:
            return {"ok": True, "data": r.json().get("data", []),
                    "meta": r.json().get("meta", {})}
        errors = r.json().get("errors", [])
        return {"ok": False, "error": errors[0].get("detail") if errors else f"HTTP {r.status_code}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def health_check() -> dict:
    """Verify App Store Connect credentials work."""
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        token = _generate_token()
        result = _get("/apps", {"limit": 1})
        return {"ok": result["ok"], "key_id": settings.key_id,
                "token_generated": bool(token)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def list_apps() -> dict[str, Any]:
    """List all iOS apps in the account."""
    result = _get("/apps", {"limit": 100})
    if result["ok"]:
        apps = [{"id": a["id"], "bundle_id": a["attributes"].get("bundleId"),
                 "name": a["attributes"].get("name"),
                 "sku": a["attributes"].get("sku"),
                 "primary_locale": a["attributes"].get("primaryLocale")}
                for a in result["data"]]
        return {"ok": True, "count": len(apps), "apps": apps}
    return result


@mcp.tool()
def get_app(app_id: str) -> dict[str, Any]:
    """Get details for a specific iOS app."""
    result = _get(f"/apps/{app_id}")
    if result["ok"]:
        d = result["data"]
        if isinstance(d, list) and d:
            d = d[0]
        return {"ok": True, "id": d.get("id"), "attributes": d.get("attributes")}
    return result


@mcp.tool()
def get_reviews(app_id: str, limit: int = 50) -> dict[str, Any]:
    """
    Get customer reviews for an app.

    Args:
        app_id: App Store Connect app ID.
        limit:  Max reviews to return (max 200).
    """
    result = _get(f"/apps/{app_id}/customerReviews",
                  {"limit": min(limit, 200), "sort": "-createdDate"})
    if result["ok"]:
        reviews = []
        for r in result["data"]:
            a = r["attributes"]
            reviews.append({
                "id": r["id"],
                "rating": a.get("rating"),
                "title": a.get("title"),
                "body": a.get("body"),
                "reviewer": a.get("reviewerNickname"),
                "territory": a.get("territory"),
                "created_at": a.get("createdDate"),
            })
        return {"ok": True, "count": len(reviews), "reviews": reviews}
    return result


@mcp.tool()
def list_builds(app_id: str, limit: int = 20) -> dict[str, Any]:
    """List TestFlight builds for an app."""
    result = _get(f"/apps/{app_id}/builds",
                  {"limit": min(limit, 200), "sort": "-uploadedDate"})
    if result["ok"]:
        builds = []
        for b in result["data"]:
            a = b["attributes"]
            builds.append({
                "id": b["id"],
                "version": a.get("version"),
                "uploaded_at": a.get("uploadedDate"),
                "expired": a.get("expired"),
                "processing_state": a.get("processingState"),
            })
        return {"ok": True, "count": len(builds), "builds": builds}
    return result


@mcp.tool()
def get_app_versions(app_id: str, state: str | None = None) -> dict[str, Any]:
    """
    Get app versions (releases) and their states.

    Args:
        app_id: App Store Connect app ID.
        state:  Filter by state (e.g. "READY_FOR_SALE", "WAITING_FOR_REVIEW").
    """
    params: dict[str, Any] = {"limit": 50}
    if state:
        params["filter[appStoreState]"] = state
    result = _get(f"/apps/{app_id}/appStoreVersions", params)
    if result["ok"]:
        versions = []
        for v in result["data"]:
            a = v["attributes"]
            versions.append({
                "id": v["id"],
                "version": a.get("versionString"),
                "state": a.get("appStoreState"),
                "platform": a.get("platform"),
                "created_at": a.get("createdDate"),
                "release_type": a.get("releaseType"),
            })
        return {"ok": True, "count": len(versions), "versions": versions}
    return result


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
