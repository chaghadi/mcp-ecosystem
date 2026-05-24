"""server.py — mcp-notifications MCP server entry point."""

from mcp.server.fastmcp import FastMCP
from src.tools import email as _email
from src.tools import sms as _sms
from src.config import settings

mcp = FastMCP(
    "mcp-notifications",
    instructions=(
        "Notifications MCP for mmiri28 solutions. "
        "Email via Resend. SMS via Twilio (international) or Termii (Nigeria +234 auto-routed). "
        "Push notifications are a stub for future implementation."
    ),
)


@mcp.tool()
def health_check() -> dict:
    """Check notification provider configuration."""
    return {
        "ok": True,
        "email": "configured" if settings.resend_api_key and "your-resend" not in settings.resend_api_key else "not configured",
        "sms_twilio": "configured" if settings.twilio_account_sid and "your-twilio" not in settings.twilio_account_sid else "not configured",
        "sms_termii": "configured" if settings.termii_api_key and "your-termii" not in settings.termii_api_key else "not configured",
        "email_from": settings.email_from,
        "termii_sender_id": settings.termii_sender_id,
        "note": "Nigerian numbers (+234) auto-route to Termii when configured.",
    }


@mcp.tool()
def send_email(
    to: str,
    subject: str,
    html: str | None = None,
    text: str | None = None,
    from_address: str | None = None,
    reply_to: str | None = None,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
) -> dict:
    """
    Send an email via Resend.

    Args:
        to:           Recipient email address.
        subject:      Email subject.
        html:         HTML body.
        text:         Plain text body (fallback if no html).
        from_address: Override sender (defaults to EMAIL_FROM).
        reply_to:     Reply-to address.
        cc, bcc:      Additional recipients.
    """
    return _email.run_send_email(
        to=to, subject=subject, html=html, text=text,
        from_address=from_address, reply_to=reply_to, cc=cc, bcc=bcc,
    )


@mcp.tool()
def send_bulk_email(
    recipients: list[str],
    subject: str,
    html: str | None = None,
    text: str | None = None,
) -> dict:
    """
    Send the same email to multiple recipients in one call.

    Args:
        recipients: List of email addresses.
        subject:    Subject line.
        html:       HTML body.
        text:       Plain text body.
    """
    return _email.run_send_bulk_email(
        recipients=recipients, subject=subject, html=html, text=text,
    )


@mcp.tool()
def send_sms(
    to: str,
    message: str,
    provider: str | None = None,
) -> dict:
    """
    Send an SMS. Nigerian numbers (+234) auto-route to Termii.

    Args:
        to:       Phone in E.164 format (e.g. +2348012345678 or +447700900123).
        message:  SMS text (max 160 chars for single SMS).
        provider: Override: "twilio" or "termii".
    """
    return _sms.run_send_sms(to=to, message=message, provider=provider)


@mcp.tool()
def send_push(user_id: str, title: str, body: str, data: dict | None = None) -> dict:
    """[STUB] Send a push notification. Requires FCM/APNs setup."""
    return {
        "ok": False, "status": "not_implemented",
        "message": "Push notifications not yet implemented. Requires FCM or APNs credentials.",
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
