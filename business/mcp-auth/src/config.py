"""config.py — Settings for mcp-auth."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class _Settings:
    def __init__(self) -> None:
        self.database_url: str   = os.getenv("DATABASE_URL", "")
        self.redis_url: str      = os.getenv("REDIS_URL", "")
        self.jwt_secret: str     = os.getenv("JWT_SECRET", "")
        self.access_token_expire_minutes: int  = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
        self.refresh_token_expire_days: int    = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "30"))
        self.superadmin_email: str = os.getenv("SUPERADMIN_EMAIL", "").lower().strip()
        self.mcp_root: Path = Path(__file__).parent.parent

    def validate(self) -> str | None:
        missing = [
            name for name, val in [
                ("DATABASE_URL", self.database_url),
                ("REDIS_URL",    self.redis_url),
                ("JWT_SECRET",   self.jwt_secret),
            ] if not val
        ]
        if missing:
            return f"Missing required config: {', '.join(missing)}"
        if self.jwt_secret in ("change-this-to-a-random-hex-string", "secret", ""):
            return "JWT_SECRET is not set to a real secret. Run: python -c \"import secrets; print(secrets.token_hex(32))\""
        return None


settings = _Settings()
