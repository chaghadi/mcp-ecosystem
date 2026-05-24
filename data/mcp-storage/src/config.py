"""config.py — Settings for mcp-storage."""

import os
from dotenv import load_dotenv

load_dotenv()


class _Settings:
    def __init__(self) -> None:
        self.account_id: str       = os.getenv("R2_ACCOUNT_ID", "")
        self.access_key_id: str    = os.getenv("R2_ACCESS_KEY_ID", "")
        self.secret_access_key: str = os.getenv("R2_SECRET_ACCESS_KEY", "")
        self.default_bucket: str   = os.getenv("R2_DEFAULT_BUCKET", "mmiri28-private")
        self.public_domain: str    = os.getenv("R2_PUBLIC_DOMAIN", "").rstrip("/")

    @property
    def endpoint_url(self) -> str:
        return f"https://{self.account_id}.r2.cloudflarestorage.com"

    def validate(self) -> str | None:
        missing = [
            name for name, val in [
                ("R2_ACCOUNT_ID", self.account_id),
                ("R2_ACCESS_KEY_ID", self.access_key_id),
                ("R2_SECRET_ACCESS_KEY", self.secret_access_key),
            ] if not val
        ]
        if missing:
            return (
                f"Missing R2 credentials: {', '.join(missing)}. "
                "Copy .env.example to .env and fill in your Cloudflare R2 API token values."
            )
        return None

    def public_url(self, key: str) -> str | None:
        """Return a stable public URL for a key, or None if no public domain is set."""
        if not self.public_domain:
            return None
        return f"{self.public_domain}/{key}"


settings = _Settings()
