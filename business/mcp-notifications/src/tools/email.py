"""email.py — Email sending via Resend."""

from typing import Any
import httpx
from src.config import settings


def run_send_email(
    to: str | list[str],
    subject: str,
    html: str | None = None,
    text: str | None = None,
    from_address: str | None = None,
    reply_to: str | None = None,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    tags: list[dict] | None = None,
) -> dict[str, Any]:
    """
    Send an email via Resend.

    Args:
        to:           Recipient email(s).
        subject:      Email subject.
        html:         HTML body.
        text:         Plain text body (fallback).
        from_address: Override sender. Defaults to EMAIL_FROM.
        reply_to:     Reply-to address.
        cc, bcc:      CC and BCC recipients.
        tags:         Resend tags for tracking: [{"name": "category", "value": "welcome"}]
    """
    if not settings.resend_api_key or "your-resend" in settings.resend_api_key:
        return {"ok": False, "error": "RESEND_API_KEY not configured. Get it from resend.com"}

    if not html and not text:
        return {"ok": False, "error": "Either html or text body is required."}

    payload: dict[str, Any] = {
        "from": from_address or settings.email_from,
        "to": to if isinstance(to, list) else [to],
        "subject": subject,
    }
    if html:   payload["html"] = html
    if text:   payload["text"] = text
    if reply_to: payload["reply_to"] = reply_to
    if cc:    payload["cc"] = cc
    if bcc:   payload["bcc"] = bcc
    if tags:  payload["tags"] = tags

    try:
        r = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.resend_api_key}",
                     "Content-Type": "application/json"},
            json=payload, timeout=10,
        )
        data = r.json()
        if r.status_code in (200, 201):
            return {"ok": True, "provider": "resend", "email_id": data.get("id"),
                    "to": payload["to"], "subject": subject}
        return {"ok": False, "error": data.get("message", f"HTTP {r.status_code}")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def run_send_bulk_email(
    recipients: list[str],
    subject: str,
    html: str | None = None,
    text: str | None = None,
    from_address: str | None = None,
) -> dict[str, Any]:
    """
    Send the same email to multiple recipients (one send call).

    Args:
        recipients: List of email addresses.
        subject:    Email subject.
        html:       HTML body.
        text:       Plain text body.
    """
    return run_send_email(
        to=recipients, subject=subject,
        html=html, text=text, from_address=from_address,
    )
