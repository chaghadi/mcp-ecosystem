"""server.py — mcp-figma-ops MCP server entry point.

Figma API operations — file metadata, components, exports, comments, variables.
Useful for design-token sync and design-system inspection.
"""

import httpx
from typing import Any
from mcp.server.fastmcp import FastMCP
from src.config import settings

mcp = FastMCP(
    "mcp-figma-ops",
    instructions="Figma MCP for mmiri28 solutions. Get file info, list components, export node images, read variables (design tokens), fetch comments.",
)


def _get(path: str, params: dict | None = None) -> dict[str, Any]:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        r = httpx.get(f"{settings.base_url}{path}",
                      headers=settings.headers, params=params or {}, timeout=30)
        if r.status_code == 200:
            return {"ok": True, "data": r.json()}
        return {"ok": False, "error": r.json().get("err", f"HTTP {r.status_code}")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def health_check() -> dict:
    """Verify Figma token."""
    result = _get("/me")
    if result["ok"]:
        user = result["data"]
        return {"ok": True, "user": user.get("handle"),
                "email": user.get("email"), "id": user.get("id")}
    return result


@mcp.tool()
def get_file(file_key: str) -> dict[str, Any]:
    """
    Get Figma file metadata, pages, and top-level nodes.

    Args:
        file_key: Figma file key from URL (e.g. "abc123" in figma.com/file/abc123/...).
    """
    result = _get(f"/files/{file_key}", {"depth": 2})
    if result["ok"]:
        d = result["data"]
        pages = []
        for page in d.get("document", {}).get("children", []):
            pages.append({
                "id": page.get("id"),
                "name": page.get("name"),
                "type": page.get("type"),
                "child_count": len(page.get("children", [])),
            })
        return {
            "ok": True, "file_key": file_key,
            "name": d.get("name"), "version": d.get("version"),
            "last_modified": d.get("lastModified"),
            "thumbnail_url": d.get("thumbnailUrl"),
            "pages": pages,
        }
    return result


@mcp.tool()
def get_file_nodes(file_key: str, node_ids: list[str]) -> dict[str, Any]:
    """
    Fetch specific nodes from a Figma file.

    Args:
        file_key: Figma file key.
        node_ids: List of node IDs (e.g. ["1:2", "3:4"]).
    """
    if not node_ids:
        return {"ok": False, "error": "node_ids cannot be empty."}
    result = _get(f"/files/{file_key}/nodes", {"ids": ",".join(node_ids)})
    if result["ok"]:
        return {"ok": True, "file_key": file_key,
                "nodes": result["data"].get("nodes", {})}
    return result


@mcp.tool()
def get_components(file_key: str) -> dict[str, Any]:
    """List all components in a Figma file."""
    result = _get(f"/files/{file_key}/components")
    if result["ok"]:
        components = []
        for c in result["data"].get("meta", {}).get("components", []):
            components.append({
                "node_id": c.get("node_id"),
                "key": c.get("key"),
                "name": c.get("name"),
                "description": c.get("description"),
                "page_name": c.get("containing_frame", {}).get("pageName"),
            })
        return {"ok": True, "file_key": file_key,
                "count": len(components), "components": components}
    return result


@mcp.tool()
def export_images(
    file_key: str, node_ids: list[str],
    format: str = "png", scale: float = 1.0,
) -> dict[str, Any]:
    """
    Export Figma nodes as images. Returns CDN URLs.

    Args:
        file_key: Figma file key.
        node_ids: Node IDs to export.
        format:   "png" | "jpg" | "svg" | "pdf"
        scale:    Image scale (1.0–4.0). Higher = bigger PNG/JPG.
    """
    if format not in {"png", "jpg", "svg", "pdf"}:
        return {"ok": False, "error": "format must be png/jpg/svg/pdf"}
    result = _get(f"/images/{file_key}",
                  {"ids": ",".join(node_ids), "format": format,
                   "scale": str(scale)})
    if result["ok"]:
        return {"ok": True, "file_key": file_key, "format": format,
                "urls": result["data"].get("images", {})}
    return result


@mcp.tool()
def get_comments(file_key: str) -> dict[str, Any]:
    """List all comments on a Figma file."""
    result = _get(f"/files/{file_key}/comments")
    if result["ok"]:
        comments = []
        for c in result["data"].get("comments", []):
            comments.append({
                "id": c.get("id"),
                "message": c.get("message"),
                "user": c.get("user", {}).get("handle"),
                "resolved": c.get("resolved_at") is not None,
                "created_at": c.get("created_at"),
            })
        return {"ok": True, "file_key": file_key,
                "count": len(comments), "comments": comments}
    return result


@mcp.tool()
def get_variables(file_key: str) -> dict[str, Any]:
    """
    Get local variables (design tokens) defined in a Figma file.
    Requires Enterprise plan for the variables API.
    """
    result = _get(f"/files/{file_key}/variables/local")
    if result["ok"]:
        d = result["data"]
        variables = []
        for var_id, var in d.get("meta", {}).get("variables", {}).items():
            variables.append({
                "id": var_id,
                "name": var.get("name"),
                "type": var.get("resolvedType"),
                "description": var.get("description"),
            })
        return {"ok": True, "file_key": file_key,
                "variable_count": len(variables), "variables": variables}
    return result


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
