"""
sms.py — SMS sending via Twilio (international) and Termii (Nigeria).

Nigerian numbers (+234) are automatically routed to Termii.
All other numbers use Twilio.
Override with explicit provider param.
"""

from typing import Any
import httpx
from src.config import settings


# ── Twilio ────────────────────────────────────────────────────────────────────

def _send_twilio(to: str, message: str) -> dict[str, Any]:
    if not settings.twilio_account_sid or "your-twilio" in settings.twilio_account_sid:
        return {"ok": False, "error": "Twilio not configured. Add TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER to .env"}

    try:
        r = httpx.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json",
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            data={"To": to, "From": settings.twilio_from, "Body": message},
            timeout=10,
        )
        data = r.json()
        if r.status_code == 201:
            return {"ok": True, "provider": "twilio", "message_sid": data.get("sid"),
                    "to": to, "status": data.get("status")}
        return {"ok": False, "provider": "twilio",
                "error": data.get("message", f"HTTP {r.status_code}")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


# ── Termii ────────────────────────────────────────────────────────────────────

def _send_termii(to: str, message: str) -> dict[str, Any]:
    if not settings.termii_api_key or "your-termii" in settings.termii_api_key:
        return {"ok": False, "error": "Termii not configured. Add TERMII_API_KEY to .env. Get it from termii.com"}

    # Termii expects numbers without +
    to_clean = to.lstrip("+")

    try:
        r = httpx.post(
            "https://api.ng.termii.com/api/sms/send",
            json={
                "to": to_clean,
                "from": settings.termii_sender_id,
                "sms": message,
                "type": "plain",
                "api_key": settings.termii_api_key,
                "channel": "generic",
            },
            timeout=10,
        )
        data = r.json()
        if r.status_code == 200 and data.get("code") == "ok":
            return {"ok": True, "provider": "termii", "message_id": data.get("message_id"),
                    "to": to, "balance": data.get("balance")}
        return {"ok": False, "provider": "termii",
                "error": data.get("message", f"HTTP {r.status_code}")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


# ── Public interface ──────────────────────────────────────────────────────────

def run_send_sms(
    to: str,
    message: str,
    provider: str | None = None,
) -> dict[str, Any]:
    """
    Send an SMS message. Nigerian numbers auto-route to Termii.

    Args:
        to:       Recipient phone number in E.164 format (e.g. +2348012345678).
        message:  SMS text. Max 160 chars for single SMS.
        provider: Override auto-routing: "twilio" or "termii".
    """
    to = to.strip()
    if not to:
        return {"ok": False, "error": "to cannot be empty."}
    if not message or not message.strip():
        return {"ok": False, "error": "message cannot be empty."}

    chosen = provider or settings.sms_provider_for(to)
    if chosen == "termii":
        return _send_termii(to, message)
    return _send_twilio(to, message)
