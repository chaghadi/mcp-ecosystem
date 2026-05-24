"""server.py — mcp-product-hunt MCP server entry point.

Product Hunt GraphQL API v2 — search, get posts, today's launches.
Posting requires user OAuth — out of scope for this MCP.
"""

import httpx
from typing import Any
from mcp.server.fastmcp import FastMCP
from src.config import settings

mcp = FastMCP(
    "mcp-product-hunt",
    instructions="Product Hunt MCP for mmiri28 solutions. Search products, get today's launches, look up posts by slug. Useful for monitoring competitors and planning launches.",
)


def _graphql(query: str, variables: dict | None = None) -> dict[str, Any]:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        r = httpx.post(settings.base_url, headers=settings.headers,
                       json={"query": query, "variables": variables or {}},
                       timeout=15)
        data = r.json()
        if "errors" in data:
            return {"ok": False, "error": data["errors"][0].get("message")}
        return {"ok": True, "data": data.get("data", {})}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def health_check() -> dict:
    """Verify Product Hunt access token."""
    result = _graphql("{ viewer { user { username } } }")
    if result["ok"]:
        user = result["data"].get("viewer", {}).get("user", {})
        return {"ok": True, "authenticated_as": user.get("username", "unknown")}
    return result


@mcp.tool()
def get_post(slug: str) -> dict[str, Any]:
    """
    Get a Product Hunt post by its slug.

    Args:
        slug: The URL slug (e.g. "linear" for producthunt.com/posts/linear).
    """
    query = """
    query Post($slug: String!) {
      post(slug: $slug) {
        id name tagline description votesCount commentsCount
        slug createdAt featuredAt url
        thumbnail { url }
        topics { edges { node { name slug } } }
        makers { name username headline twitterUsername }
      }
    }
    """
    result = _graphql(query, {"slug": slug})
    if result["ok"]:
        post = result["data"].get("post")
        if not post:
            return {"ok": False, "error": "Post not found"}
        return {"ok": True, "post": {
            "id": post["id"], "name": post["name"], "tagline": post["tagline"],
            "votes": post["votesCount"], "comments": post["commentsCount"],
            "url": post["url"], "created_at": post["createdAt"],
            "featured_at": post.get("featuredAt"),
            "topics": [e["node"]["name"] for e in post["topics"]["edges"]],
            "makers": [{"name": m["name"], "username": m["username"]} for m in post["makers"]],
        }}
    return result


@mcp.tool()
def get_todays_posts(limit: int = 20) -> dict[str, Any]:
    """
    Get today's top Product Hunt launches.

    Args:
        limit: Max posts to return (default 20, max 50).
    """
    query = """
    query TodaysPosts($first: Int!) {
      posts(first: $first, order: VOTES) {
        edges { node {
          id name tagline votesCount commentsCount slug url featuredAt
          topics { edges { node { name } } }
        } }
      }
    }
    """
    result = _graphql(query, {"first": min(limit, 50)})
    if result["ok"]:
        edges = result["data"].get("posts", {}).get("edges", [])
        posts = []
        for e in edges:
            n = e["node"]
            posts.append({
                "name": n["name"], "tagline": n["tagline"],
                "votes": n["votesCount"], "comments": n["commentsCount"],
                "url": n["url"], "slug": n["slug"],
                "topics": [t["node"]["name"] for t in n["topics"]["edges"]],
            })
        return {"ok": True, "count": len(posts), "posts": posts}
    return result


@mcp.tool()
def search_posts(query: str, limit: int = 20) -> dict[str, Any]:
    """
    Search Product Hunt posts.

    Args:
        query: Search term.
        limit: Max results.
    """
    gql = """
    query Search($query: String, $first: Int!) {
      posts(query: $query, first: $first) {
        edges { node {
          name tagline votesCount slug url
        } }
      }
    }
    """
    result = _graphql(gql, {"query": query, "first": min(limit, 50)})
    if result["ok"]:
        edges = result["data"].get("posts", {}).get("edges", [])
        posts = [{"name": e["node"]["name"], "tagline": e["node"]["tagline"],
                  "votes": e["node"]["votesCount"], "url": e["node"]["url"]}
                 for e in edges]
        return {"ok": True, "query": query, "count": len(posts), "posts": posts}
    return result


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
