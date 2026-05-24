"""server.py — mcp-playstore MCP server entry point.

Google Play Developer API — manage Android apps.
Uses service account auth (JSON key from Google Cloud Console).

Setup:
1. Google Cloud Console → IAM → Service Accounts → Create + download JSON key
2. Play Console → Setup → API access → Grant access to the service account
3. Set GOOGLE_SERVICE_ACCOUNT_PATH=/path/to/service-account.json
"""

import json
from typing import Any

import httpx
from google.oauth2 import service_account
from google.auth.transport.requests import Request

from mcp.server.fastmcp import FastMCP
from src.config import settings

mcp = FastMCP(
    "mcp-playstore",
    instructions="Google Play Console MCP for mmiri28 solutions. Manage Android app listings, fetch reviews, list release tracks.",
)

SCOPE = ["https://www.googleapis.com/auth/androidpublisher"]


def _credentials():
    if settings.service_account_json:
        info = json.loads(settings.service_account_json)
        return service_account.Credentials.from_service_account_info(info, scopes=SCOPE)
    return service_account.Credentials.from_service_account_file(
        settings.service_account_path, scopes=SCOPE)


def _access_token() -> str:
    creds = _credentials()
    creds.refresh(Request())
    return creds.token


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_access_token()}"}


def _get(path: str, params: dict | None = None) -> dict[str, Any]:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        r = httpx.get(f"{settings.base_url}{path}",
                      headers=_headers(), params=params or {}, timeout=15)
        if r.status_code == 200:
            return {"ok": True, "data": r.json()}
        try:
            err_msg = r.json().get("error", {}).get("message", f"HTTP {r.status_code}")
        except Exception:
            err_msg = f"HTTP {r.status_code}: {r.text[:200]}"
        return {"ok": False, "error": err_msg}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def health_check() -> dict:
    """Verify service account credentials."""
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        token = _access_token()
        return {"ok": True, "auth": "configured", "token_obtained": bool(token)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def get_app_listing(package_name: str, language: str = "en-US") -> dict[str, Any]:
    """
    Get the store listing for an Android app in a specific language.

    Args:
        package_name: App package (e.g. "com.mmiri28.marketplace").
        language:     BCP-47 language code. Default: "en-US".

    Note: Google Play requires opening an "edit" session for read access.
    This endpoint creates one and immediately reads.
    """
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        # Open an edit
        r = httpx.post(f"{settings.base_url}/applications/{package_name}/edits",
                       headers=_headers(), timeout=15)
        if r.status_code != 200:
            return {"ok": False, "error": f"Could not open edit: HTTP {r.status_code}"}
        edit_id = r.json()["id"]

        # Read listing
        r = httpx.get(
            f"{settings.base_url}/applications/{package_name}/edits/{edit_id}/listings/{language}",
            headers=_headers(), timeout=15,
        )
        # Clean up edit (don't commit it)
        httpx.delete(f"{settings.base_url}/applications/{package_name}/edits/{edit_id}",
                     headers=_headers(), timeout=10)

        if r.status_code == 200:
            return {"ok": True, "package_name": package_name, "language": language,
                    "listing": r.json()}
        return {"ok": False, "error": f"HTTP {r.status_code}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def list_reviews(package_name: str, max_results: int = 50) -> dict[str, Any]:
    """
    Get recent reviews for an Android app.

    Args:
        package_name: App package name.
        max_results:  Max reviews (max 100).
    """
    result = _get(f"/applications/{package_name}/reviews",
                  {"maxResults": min(max_results, 100)})
    if result["ok"]:
        reviews = []
        for r in result["data"].get("reviews", []):
            comments = r.get("comments", [])
            user_comment = next((c.get("userComment", {}) for c in comments if "userComment" in c), {})
            reviews.append({
                "review_id": r.get("reviewId"),
                "author": r.get("authorName"),
                "rating": user_comment.get("starRating"),
                "text": user_comment.get("text"),
                "device": user_comment.get("deviceMetadata", {}).get("productName"),
                "android_version": user_comment.get("androidOsVersion"),
                "app_version": user_comment.get("appVersionName"),
            })
        return {"ok": True, "package_name": package_name,
                "count": len(reviews), "reviews": reviews}
    return result


@mcp.tool()
def list_tracks(package_name: str) -> dict[str, Any]:
    """
    List release tracks (production, beta, alpha, internal).

    Args:
        package_name: App package name.
    """
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        # Open edit
        r = httpx.post(f"{settings.base_url}/applications/{package_name}/edits",
                       headers=_headers(), timeout=15)
        if r.status_code != 200:
            return {"ok": False, "error": f"Could not open edit: HTTP {r.status_code}"}
        edit_id = r.json()["id"]

        r = httpx.get(f"{settings.base_url}/applications/{package_name}/edits/{edit_id}/tracks",
                      headers=_headers(), timeout=15)
        httpx.delete(f"{settings.base_url}/applications/{package_name}/edits/{edit_id}",
                     headers=_headers(), timeout=10)

        if r.status_code == 200:
            tracks = []
            for t in r.json().get("tracks", []):
                releases = t.get("releases", [])
                latest = releases[0] if releases else {}
                tracks.append({
                    "track": t.get("track"),
                    "status": latest.get("status"),
                    "version_codes": latest.get("versionCodes", []),
                    "release_name": latest.get("name"),
                    "user_fraction": latest.get("userFraction"),
                })
            return {"ok": True, "package_name": package_name, "tracks": tracks}
        return {"ok": False, "error": f"HTTP {r.status_code}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
