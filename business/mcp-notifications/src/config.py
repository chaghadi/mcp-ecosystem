"""config.py — Settings for mcp-notifications."""

import os
from dotenv import load_dotenv

load_dotenv()


class _Settings:
    def __init__(self) -> None:
        self.resend_api_key: str    = os.getenv("RESEND_API_KEY", "")
        self.email_from: str        = os.getenv("EMAIL_FROM", "noreply@mmiri28.com")
        self.twilio_account_sid: str = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.twilio_auth_token: str  = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.twilio_from: str        = os.getenv("TWILIO_FROM_NUMBER", "")
        self.termii_api_key: str     = os.getenv("TERMII_API_KEY", "")
        self.termii_sender_id: str   = os.getenv("TERMII_SENDER_ID", "mmiri28")

    def sms_provider_for(self, to: str) -> str:
        """Route Nigerian numbers to Termii, everything else to Twilio."""
        if to.startswith("+234") or to.startswith("234"):
            return "termii"
        return "twilio"


settings = _Settings()
