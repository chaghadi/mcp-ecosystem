"""
config.py — Settings for mcp-redis.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class _Settings:
    def __init__(self) -> None:
        self.redis_url: str = os.getenv("REDIS_URL", "")
        self.key_prefix: str = os.getenv("KEY_PREFIX", "mmiri28")

    def validate(self) -> str | None:
        if not self.redis_url:
            return (
                "REDIS_URL is not set. "
                "Copy .env.example to .env and add your Upstash connection string."
            )
        if not (self.redis_url.startswith("redis://") or
                self.redis_url.startswith("rediss://")):
            return (
                f"REDIS_URL does not look like a Redis URL: {self.redis_url!r}. "
                "Expected: redis:// or rediss://"
            )
        return None

    def prefixed(self, key: str) -> str:
        """Add the namespace prefix to a key."""
        return f"{self.key_prefix}:{key}"


settings = _Settings()
