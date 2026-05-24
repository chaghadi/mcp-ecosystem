"""server.py — mcp-seo MCP server entry point.

SEO analysis tools — meta tags, page speed, sitemap generation, robots.txt.
Pure Python — no API credentials needed for basic analysis.
PageSpeed requires Google API key (free tier).
"""

import os
import httpx
from typing import Any
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

mcp = FastMCP(
    "mcp-seo",
    instructions="SEO analysis MCP for mmiri28 solutions. Analyze meta tags, generate sitemaps, check robots.txt, measure page speed.",
)

PAGESPEED_KEY = os.getenv("PAGESPEED_API_KEY", "")


@mcp.tool()
def health_check() -> dict:
    """mcp-seo works without credentials for basic features."""
    return {
        "ok": True,
        "basic_analysis": "ready (no credentials needed)",
        "pagespeed_api": "configured" if PAGESPEED_KEY and "your-" not in PAGESPEED_KEY else "not configured (optional)",
    }


@mcp.tool()
def analyze_page(url: str) -> dict[str, Any]:
    """
    Analyze a webpage for basic SEO factors.

    Returns: title, meta description, h1-h6 counts, image alts,
    canonical URL, social tags, word count.

    Args:
        url: Full URL to analyze.
    """
    try:
        r = httpx.get(url, timeout=15, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0 (mmiri28-seo-bot)"})
        if r.status_code != 200:
            return {"ok": False, "error": f"HTTP {r.status_code}"}

        soup = BeautifulSoup(r.text, "html.parser")

        title = soup.title.string.strip() if soup.title else None
        meta_desc = soup.find("meta", attrs={"name": "description"})
        meta_desc = meta_desc.get("content", "").strip() if meta_desc else None

        canonical = soup.find("link", rel="canonical")
        canonical = canonical.get("href") if canonical else None

        # Social tags
        og_title = soup.find("meta", property="og:title")
        og_desc  = soup.find("meta", property="og:description")
        og_image = soup.find("meta", property="og:image")
        twitter_card = soup.find("meta", attrs={"name": "twitter:card"})

        # Heading counts
        headings = {f"h{i}": len(soup.find_all(f"h{i}")) for i in range(1, 7)}

        # Image analysis
        images = soup.find_all("img")
        images_missing_alt = sum(1 for img in images if not img.get("alt"))

        # Word count (text only)
        body_text = soup.get_text(separator=" ", strip=True)
        word_count = len(body_text.split())

        # Issues
        issues = []
        if not title:
            issues.append("Missing <title> tag")
        elif len(title) > 60:
            issues.append(f"Title too long ({len(title)} chars, ideal: 50-60)")
        elif len(title) < 30:
            issues.append(f"Title too short ({len(title)} chars, ideal: 50-60)")

        if not meta_desc:
            issues.append("Missing meta description")
        elif len(meta_desc) > 160:
            issues.append(f"Meta description too long ({len(meta_desc)} chars, ideal: 150-160)")

        if headings["h1"] == 0:
            issues.append("Missing H1 tag")
        elif headings["h1"] > 1:
            issues.append(f"Multiple H1 tags ({headings['h1']})")

        if images_missing_alt > 0:
            issues.append(f"{images_missing_alt} images missing alt text")

        if word_count < 300:
            issues.append(f"Thin content ({word_count} words, recommended: 300+)")

        score = max(0, 100 - (len(issues) * 10))

        return {
            "ok": True, "url": url, "score": score,
            "title": title, "title_length": len(title) if title else 0,
            "meta_description": meta_desc,
            "meta_description_length": len(meta_desc) if meta_desc else 0,
            "canonical": canonical,
            "headings": headings,
            "images_total": len(images),
            "images_missing_alt": images_missing_alt,
            "word_count": word_count,
            "social_tags": {
                "og_title": bool(og_title), "og_description": bool(og_desc),
                "og_image": bool(og_image), "twitter_card": bool(twitter_card),
            },
            "issues": issues,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def check_meta_tags(url: str) -> dict[str, Any]:
    """Check specifically which meta tags are present and their values."""
    try:
        r = httpx.get(url, timeout=15, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        tags = {}
        for tag in soup.find_all("meta"):
            name = tag.get("name") or tag.get("property") or tag.get("http-equiv")
            content = tag.get("content")
            if name and content:
                tags[name] = content
        return {"ok": True, "url": url, "meta_count": len(tags), "meta_tags": tags}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def generate_sitemap(urls: list[dict]) -> dict[str, Any]:
    """
    Generate a sitemap.xml from a list of URLs.

    Args:
        urls: List of dicts: [{"loc": "https://...", "lastmod": "2026-01-01", "priority": 0.8, "changefreq": "weekly"}]
    """
    if not urls:
        return {"ok": False, "error": "urls list cannot be empty."}

    xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>',
                 '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']

    for item in urls:
        loc = item.get("loc")
        if not loc:
            continue
        xml_lines.append("  <url>")
        xml_lines.append(f"    <loc>{loc}</loc>")
        if "lastmod" in item:
            xml_lines.append(f"    <lastmod>{item['lastmod']}</lastmod>")
        if "changefreq" in item:
            xml_lines.append(f"    <changefreq>{item['changefreq']}</changefreq>")
        if "priority" in item:
            xml_lines.append(f"    <priority>{item['priority']}</priority>")
        xml_lines.append("  </url>")
    xml_lines.append("</urlset>")

    sitemap_xml = "\n".join(xml_lines)
    return {
        "ok": True, "url_count": len(urls),
        "sitemap_xml": sitemap_xml,
        "size_bytes": len(sitemap_xml),
    }


@mcp.tool()
def check_robots_txt(domain: str) -> dict[str, Any]:
    """Fetch and parse a domain's robots.txt file."""
    url = f"https://{domain.replace('https://', '').replace('http://', '').strip('/')}/robots.txt"
    try:
        r = httpx.get(url, timeout=10, follow_redirects=True)
        if r.status_code != 200:
            return {"ok": False, "error": f"robots.txt not found (HTTP {r.status_code})"}

        rules = {"User-agent": [], "Allow": [], "Disallow": [], "Sitemap": []}
        for line in r.text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                if key in rules:
                    rules[key].append(value.strip())

        return {"ok": True, "url": url, "rules": rules, "raw": r.text[:2000]}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def lighthouse_score(url: str, strategy: str = "mobile") -> dict[str, Any]:
    """
    Get a Google Lighthouse score via the PageSpeed Insights API.

    Args:
        url:      Page to test.
        strategy: "mobile" or "desktop".
    """
    if not PAGESPEED_KEY or "your-" in PAGESPEED_KEY:
        return {"ok": False, "error": "PAGESPEED_API_KEY not set. Get it free from console.cloud.google.com (PageSpeed Insights API)."}

    try:
        r = httpx.get(
            "https://www.googleapis.com/pagespeedonline/v5/runPagespeed",
            params={
                "url": url, "key": PAGESPEED_KEY, "strategy": strategy,
                "category": "performance"
            },
            timeout=30,
        )
        data = r.json()
        if r.status_code != 200:
            return {"ok": False, "error": data.get("error", {}).get("message", "Unknown")}

        lighthouse = data.get("lighthouseResult", {})
        categories = lighthouse.get("categories", {})
        performance = categories.get("performance", {}).get("score", 0)

        return {
            "ok": True, "url": url, "strategy": strategy,
            "performance_score": int(performance * 100),
            "first_contentful_paint": lighthouse.get("audits", {}).get("first-contentful-paint", {}).get("displayValue"),
            "largest_contentful_paint": lighthouse.get("audits", {}).get("largest-contentful-paint", {}).get("displayValue"),
            "cumulative_layout_shift": lighthouse.get("audits", {}).get("cumulative-layout-shift", {}).get("displayValue"),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
