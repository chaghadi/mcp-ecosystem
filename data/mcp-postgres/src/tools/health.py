"""
health.py — Database health check tool.
"""

from typing import Any

from src.db import check_connectivity


def run() -> dict[str, Any]:
    """
    Check database connectivity.

    Connects, runs SELECT version(), returns status and PostgreSQL version.
    Safe to call at any time — does not modify any data.
    """
    result = check_connectivity()

    if result["ok"]:
        return {
            "ok": True,
            "status": "connected",
            "postgres_version": result["version"],
            "message": "Database is reachable.",
        }

    return {
        "ok": False,
        "status": "unreachable",
        "error": result["error"],
        "message": (
            "Cannot reach the database. Check DATABASE_URL in .env "
            "and confirm your Supabase project is active."
        ),
    }
