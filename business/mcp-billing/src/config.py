"""config.py — Settings for mcp-billing."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PAYSTACK_CURRENCIES = {"NGN", "GHS", "ZAR", "KES", "XOF", "EGP"}


class _Settings:
    def __init__(self) -> None:
        self.stripe_secret_key: str     = os.getenv("STRIPE_SECRET_KEY", "")
        self.stripe_webhook_secret: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
        self.paystack_secret_key: str   = os.getenv("PAYSTACK_SECRET_KEY", "")
        self.database_url: str          = os.getenv("DATABASE_URL", "")
        self.default_currency: str      = os.getenv("DEFAULT_CURRENCY", "USD").upper()
        self.mcp_root: Path             = Path(__file__).parent.parent

    def provider_for(self, currency: str | None = None, explicit: str | None = None) -> str:
        """Return 'stripe' or 'paystack' based on currency or explicit override."""
        if explicit and explicit.lower() in ("stripe", "paystack"):
            return explicit.lower()
        c = (currency or self.default_currency).upper()
        return "paystack" if c in PAYSTACK_CURRENCIES else "stripe"

    def validate_stripe(self) -> str | None:
        if not self.stripe_secret_key or "your-stripe" in self.stripe_secret_key:
            return "STRIPE_SECRET_KEY not configured. Get it from dashboard.stripe.com"
        return None

    def validate_paystack(self) -> str | None:
        if not self.paystack_secret_key or "your-paystack" in self.paystack_secret_key:
            return "PAYSTACK_SECRET_KEY not configured. Get it from dashboard.paystack.com"
        return None

    def validate(self, provider: str = "stripe") -> str | None:
        if not self.database_url:
            return "DATABASE_URL is not set."
        if provider == "stripe":
            return self.validate_stripe()
        if provider == "paystack":
            return self.validate_paystack()
        return None


settings = _Settings()
