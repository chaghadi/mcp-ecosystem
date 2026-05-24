"""config.py — Settings for mcp-user-mgmt."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class _Settings:
    def __init__(self) -> None:
        self.database_url: str = os.getenv("DATABASE_URL", "")
        self.mcp_root: Path = Path(__file__).parent.parent

    def validate(self) -> str | None:
        if not self.database_url:
            return "DATABASE_URL is not set. Copy .env.example to .env."
        return None


settings = _Settings()
