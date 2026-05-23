"""
config.py — Central settings for mcp-blueprint.

All tools import `settings` from here. Environment variables are loaded once
at startup via python-dotenv. Override any value in your .env file.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class _Settings:
    def __init__(self) -> None:
        self.brand: str = os.getenv("BRAND", "mmiri28 solutions")
        self.owner: str = os.getenv("OWNER", "chaghadi")

        _data_dir_env = os.getenv("BLUEPRINT_DATA_DIR", "")
        if _data_dir_env:
            self.data_dir = Path(_data_dir_env)
        else:
            # Default: ./data relative to the mcp-blueprint root
            self.data_dir = Path(__file__).parent.parent / "data"

        # Ensure the data directory exists at startup
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def __repr__(self) -> str:
        return (
            f"Settings(brand={self.brand!r}, owner={self.owner!r}, "
            f"data_dir={self.data_dir})"
        )


settings = _Settings()
