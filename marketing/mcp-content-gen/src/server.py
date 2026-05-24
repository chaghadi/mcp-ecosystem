"""server.py — mcp-content-gen MCP server entry point.

AI-powered content generation using Claude API.
Generates blog posts, social posts, email subjects, meta descriptions.
"""

import os
from typing import Any
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

mcp = FastMCP(
    "mcp-content-gen",
    instructions="AI content generation MCP for mmiri28 solutions. Uses Claude API to generate blog posts, social posts, email subjects, and other marketing copy.",
)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = os.getenv("CONTENT_GEN_MODEL", "claude-sonnet-4-5")


def _validate():
    if not ANTHROPIC_API_KEY or "your-" in ANTHROPIC_API_KEY:
        return "ANTHROPIC_API_KEY not configured. Get it from console.anthropic.com"
    return None


def _generate(system: str, user: str, max_tokens: int = 1024) -> dict[str, Any]:
    """Call Claude API and return the text response."""
    err = _validate()
    if err: return {"ok": False, "error": err}

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=MODEL, max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(block.text for block in response.content if hasattr(block, "text"))
        return {
            "ok": True, "content": text,
            "model": MODEL,
            "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def health_check() -> dict:
    err = _validate()
    if err: return {"ok": False, "error": err}
    return {"ok": True, "model": MODEL, "status": "ready"}


@mcp.tool()
def generate_blog_post(
    topic: str, tone: str = "professional",
    word_count: int = 800, audience: str = "general",
) -> dict[str, Any]:
    """
    Generate a blog post on a given topic.

    Args:
        topic:      Blog post subject.
        tone:       "professional", "casual", "technical", "friendly".
        word_count: Approximate length.
        audience:   Target audience (e.g. "developers", "small business owners").
    """
    system = f"You are a professional content writer. Write engaging, well-structured blog posts in a {tone} tone for {audience}. Use markdown formatting with headers and lists."
    user = f"Write a {word_count}-word blog post about: {topic}\n\nInclude an attention-grabbing introduction, 3-4 main sections with subheadings, and a strong conclusion."
    return _generate(system, user, max_tokens=2000)


@mcp.tool()
def generate_social_post(
    platform: str, topic: str, tone: str = "engaging",
) -> dict[str, Any]:
    """
    Generate a social media post optimized for a specific platform.

    Args:
        platform: "twitter", "linkedin", "facebook", "instagram".
        topic:    What to post about.
        tone:     "engaging", "professional", "casual", "promotional".
    """
    limits = {"twitter": 280, "linkedin": 3000, "facebook": 2000, "instagram": 2200}
    limit = limits.get(platform.lower(), 280)

    system = f"You are a social media expert. Write posts that get high engagement on {platform}. Stay under {limit} characters. Use a {tone} tone."
    user = f"Write a {platform} post about: {topic}\n\nMake it scroll-stopping. Include relevant emojis sparingly. End with a question or call-to-action when appropriate."
    return _generate(system, user, max_tokens=800)


@mcp.tool()
def generate_email_subject(
    topic: str, intent: str = "newsletter",
    count: int = 5,
) -> dict[str, Any]:
    """
    Generate email subject lines optimized for open rates.

    Args:
        topic:  What the email is about.
        intent: "newsletter", "promotional", "transactional", "announcement".
        count:  Number of variants to generate.
    """
    system = "You are an email marketing expert. Write subject lines that maximize open rates while avoiding spam triggers. Keep them under 50 characters."
    user = f"Generate {count} different email subject lines for a {intent} email about: {topic}\n\nReturn as a numbered list. Use varied approaches: curiosity, urgency, benefit, question, personalization."
    return _generate(system, user, max_tokens=500)


@mcp.tool()
def generate_meta_description(
    page_content: str, target_keyword: str = "",
) -> dict[str, Any]:
    """
    Generate an SEO meta description for a webpage.

    Args:
        page_content:    The page content or summary.
        target_keyword:  Primary SEO keyword to include.
    """
    system = "You are an SEO expert. Write meta descriptions that drive clicks. Stay between 150-160 characters. Include the target keyword naturally."
    user = f"Write a meta description.\n\nTarget keyword: {target_keyword or 'none specified'}\n\nPage content:\n{page_content[:2000]}"
    return _generate(system, user, max_tokens=300)


@mcp.tool()
def rewrite(
    text: str, tone: str = "professional",
    audience: str = "general", purpose: str = "clarify",
) -> dict[str, Any]:
    """
    Rewrite text in a different tone or for a different audience.

    Args:
        text:     Original text.
        tone:     Target tone.
        audience: Target audience.
        purpose:  "clarify", "shorten", "expand", "translate-formal", "translate-casual".
    """
    system = f"You are an editor. Rewrite text in a {tone} tone for {audience}. Purpose: {purpose}."
    user = f"Rewrite this text:\n\n{text}"
    return _generate(system, user, max_tokens=len(text.split()) * 4 + 200)


@mcp.tool()
def generate_product_description(
    product_name: str, features: list[str],
    audience: str = "general", tone: str = "persuasive",
) -> dict[str, Any]:
    """
    Generate a product description for ecommerce or landing pages.

    Args:
        product_name: Name of the product.
        features:     List of key features or benefits.
        audience:     Target customer.
        tone:         "persuasive", "technical", "playful", "luxury".
    """
    system = f"You are a copywriter. Write product descriptions in a {tone} tone for {audience}. Focus on benefits, not just features."
    user = f"Write a product description for: {product_name}\n\nKey features:\n" + "\n".join(f"- {f}" for f in features) + "\n\nInclude a hook, 2-3 benefit-focused paragraphs, and a call-to-action."
    return _generate(system, user, max_tokens=800)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
