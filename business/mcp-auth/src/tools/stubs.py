"""
stubs.py — Unimplemented tools registered so Claude Code can see them.

oauth_redirect()   — Google OAuth redirect URL (needs OAuth app credentials)
oauth_callback()   — Google OAuth callback handler
send_verification()— Send email/phone verification code (needs mcp-notifications)
verify_code()      — Verify email/phone code
"""

from typing import Any


def not_implemented(tool: str, detail: str = "") -> dict[str, Any]:
    return {
        "ok": False,
        "status": "not_implemented",
        "tool": tool,
        "detail": detail,
        "next": f"Implement src/tools/{tool}.py and register in server.py",
    }


def run_oauth_redirect(provider: str, app_slug: str) -> dict[str, Any]:
    """
    [STUB] Generate a Google OAuth redirect URL.

    Will require: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET in .env.
    Returns a URL the client redirects the user to for Google login.
    """
    return not_implemented(
        "oauth_redirect",
        f"provider={provider}, app_slug={app_slug}. "
        "Needs GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET configured."
    )


def run_oauth_callback(provider: str, code: str, state: str) -> dict[str, Any]:
    """
    [STUB] Handle the OAuth callback after Google redirects back.

    Exchanges the code for tokens, creates or links the user account,
    returns JWT tokens identical to login().
    """
    return not_implemented(
        "oauth_callback",
        f"provider={provider}. Needs oauth_redirect implemented first."
    )


def run_send_verification(user_id: str, method: str) -> dict[str, Any]:
    """
    [STUB] Send an email or SMS verification code to the user.

    Requires mcp-notifications to be built and active.
    method: "email" | "phone"
    """
    return not_implemented(
        "send_verification",
        f"user_id={user_id}, method={method}. Requires mcp-notifications."
    )


def run_verify_code(user_id: str, code: str) -> dict[str, Any]:
    """
    [STUB] Verify an email or phone verification code.

    Sets is_verified=true on the user if the code is correct.
    """
    return not_implemented(
        "verify_code",
        f"user_id={user_id}. Requires send_verification to be implemented first."
    )
