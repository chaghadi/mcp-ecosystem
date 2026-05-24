"""
config.py — Settings for mcp-postgres.

Reads DATABASE_URL from .env. All tools import `settings` from here.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class _Settings:
    def __init__(self) -> None:
        self.database_url: str = os.environ.get("DATABASE_URL", "")
        # Root of this MCP — used by migrate tools to locate alembic.ini
        self.mcp_root: Path = Path(__file__).parent.parent

    def validate(self) -> str | None:
        """Return an error string if config is invalid, else None."""
        if not self.database_url:
            return (
                "DATABASE_URL is not set. "
                "Copy .env.example to .env and add your Supabase connection string."
            )
        if not self.database_url.startswith("postgresql"):
            return (
                f"DATABASE_URL does not look like a PostgreSQL URL: {self.database_url!r}. "
                "Expected format: postgresql://user:pass@host:port/db"
            )
        return None


settings = _Settings()
