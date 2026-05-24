"""health.py — R2 connectivity check."""

from src.client import check_connectivity
from src.config import settings


def run() -> dict:
    """Verify R2 credentials by listing buckets."""
    result = check_connectivity()
    if result["ok"]:
        return {
            "ok": True,
            "status": "connected",
            "endpoint": settings.endpoint_url,
            "buckets": result["buckets"],
            "public_domain": settings.public_domain or "not configured",
            "message": f"R2 connected. {len(result['buckets'])} bucket(s) found.",
        }
    return {
        "ok": False,
        "status": "unreachable",
        "error": result["error"],
        "message": "Cannot reach R2. Check R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY in .env.",
    }
