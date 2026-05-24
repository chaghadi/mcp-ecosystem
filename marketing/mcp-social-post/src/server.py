"""server.py — mcp-social-post MCP server entry point.

Post to Twitter/X (via tweepy) and LinkedIn (via REST API).
Facebook and Instagram are stubs for future implementation.
"""

import httpx
from typing import Any
from mcp.server.fastmcp import FastMCP
from src.config import settings

mcp = FastMCP(
    "mcp-social-post",
    instructions="Social media posting MCP for mmiri28 solutions. Post to Twitter/X and LinkedIn. Returns the published URL.",
)


@mcp.tool()
def health_check() -> dict:
    """Check which social platforms are configured."""
    return {
        "ok": True,
        "twitter": "configured" if not settings.validate_twitter() else "not configured",
        "linkedin": "configured" if not settings.validate_linkedin() else "not configured",
        "facebook": "stub (not implemented)",
        "instagram": "stub (not implemented)",
    }


@mcp.tool()
def post_twitter(text: str, reply_to_id: str | None = None) -> dict[str, Any]:
    """
    Post a tweet to Twitter/X.

    Args:
        text:         Tweet content (max 280 chars).
        reply_to_id:  Optional tweet ID to reply to.
    """
    err = settings.validate_twitter()
    if err: return {"ok": False, "error": err}

    if len(text) > 280:
        return {"ok": False, "error": f"Tweet too long ({len(text)} chars, max 280)."}

    try:
        import tweepy
        client = tweepy.Client(
            consumer_key=settings.twitter_api_key,
            consumer_secret=settings.twitter_api_secret,
            access_token=settings.twitter_access_token,
            access_token_secret=settings.twitter_access_secret,
        )
        kwargs = {"text": text}
        if reply_to_id:
            kwargs["in_reply_to_tweet_id"] = reply_to_id
        response = client.create_tweet(**kwargs)

        if response.data:
            tweet_id = response.data["id"]
            return {
                "ok": True, "platform": "twitter",
                "tweet_id": tweet_id,
                "url": f"https://twitter.com/i/web/status/{tweet_id}",
                "text": text,
            }
        return {"ok": False, "error": "Failed to post tweet."}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def post_linkedin(text: str, visibility: str = "PUBLIC") -> dict[str, Any]:
    """
    Post text to LinkedIn (personal account).

    Args:
        text:       Post content.
        visibility: "PUBLIC" or "CONNECTIONS".
    """
    err = settings.validate_linkedin()
    if err: return {"ok": False, "error": err}

    if not settings.linkedin_author_urn:
        return {"ok": False, "error": "LINKEDIN_AUTHOR_URN not set. Get your URN from linkedin.com/me"}

    try:
        r = httpx.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers={
                "Authorization": f"Bearer {settings.linkedin_access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            },
            json={
                "author": settings.linkedin_author_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": text},
                        "shareMediaCategory": "NONE",
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": visibility},
            },
            timeout=15,
        )
        if r.status_code in (200, 201):
            post_id = r.headers.get("X-RestLi-Id", "unknown")
            return {
                "ok": True, "platform": "linkedin",
                "post_id": post_id,
                "url": f"https://www.linkedin.com/feed/update/{post_id}/",
                "text": text,
            }
        return {"ok": False, "error": f"HTTP {r.status_code}: {r.text[:200]}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def post_to_all(text: str, platforms: list[str] | None = None) -> dict[str, Any]:
    """
    Cross-post to multiple platforms.

    Args:
        text:      Post content (will be truncated to 280 for Twitter).
        platforms: List like ["twitter", "linkedin"]. Default: all configured.
    """
    targets = platforms or ["twitter", "linkedin"]
    results = []

    if "twitter" in targets:
        tweet_text = text[:280]
        r = post_twitter(tweet_text)
        results.append({"platform": "twitter", **r})

    if "linkedin" in targets:
        r = post_linkedin(text)
        results.append({"platform": "linkedin", **r})

    successful = [r for r in results if r.get("ok")]
    return {
        "ok": len(successful) > 0,
        "platforms_posted": [r["platform"] for r in successful],
        "results": results,
    }


@mcp.tool()
def post_facebook(page_id: str, message: str) -> dict[str, Any]:
    """[STUB] Post to a Facebook page. Requires Meta Business approval."""
    return {"ok": False, "status": "not_implemented",
            "message": "Facebook posting requires Meta Business app + page access token."}


@mcp.tool()
def post_instagram(caption: str, media_url: str) -> dict[str, Any]:
    """[STUB] Post to Instagram. Requires Meta Business account + Graph API access."""
    return {"ok": False, "status": "not_implemented",
            "message": "Instagram posting requires Meta Business approval and a business/creator account."}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
