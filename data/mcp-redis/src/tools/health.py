"""health.py — Redis health check."""

from src.client import check_connectivity


def run() -> dict:
    """Ping Redis and return version and mode."""
    result = check_connectivity()
    if result["ok"]:
        return {
            "ok": True,
            "status": "connected",
            "redis_version": result["redis_version"],
            "mode": result["mode"],
            "message": "Redis is reachable.",
        }
    return {
        "ok": False,
        "status": "unreachable",
        "error": result["error"],
        "message": (
            "Cannot reach Redis. Check REDIS_URL in .env "
            "and confirm your Upstash database is active."
        ),
    }
