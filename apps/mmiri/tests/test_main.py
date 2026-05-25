"""Tests for mmiri.

These verify the app structure imports cleanly without requiring
a real database connection or running MCPs.
"""

import sys
from pathlib import Path

# Ensure the app's package root is importable when running pytest from this dir
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_app_imports():
    """The FastAPI app object can be constructed."""
    from src.main import app
    assert app.title == "mmiri"
    assert app.version == "0.2.0"


def test_routes_registered():
    """Required routes are defined."""
    from src.main import app
    paths = {route.path for route in app.routes}
    assert "/" in paths
    assert "/api/health" in paths
    assert "/api/visit-count" in paths


def test_mcp_client_resolves_ecosystem_root():
    """MCPClient finds the ecosystem root and refuses to start an MCP that doesn't exist."""
    from src.mcp_client import MCPClient, ECOSYSTEM_ROOT
    assert ECOSYSTEM_ROOT.name == "mcp-ecosystem"
    client = MCPClient("mcp-analytics", "business")
    assert client.cwd.exists()
    assert client.mcp_name == "mcp-analytics"


def test_static_files_exist():
    """Banner HTML, CSS, JS, and the MCP catalog are present."""
    from src.main import STATIC_DIR
    import json
    assert (STATIC_DIR / "index.html").exists()
    assert (STATIC_DIR / "style.css").exists()
    assert (STATIC_DIR / "app.js").exists()
    assert (STATIC_DIR / "catalog.json").exists()

    html = (STATIC_DIR / "index.html").read_text()
    assert "mmiri" in html
    assert "ogbe" in html

    catalog = json.loads((STATIC_DIR / "catalog.json").read_text())
    assert len(catalog) >= 40, f"expected ~47 MCPs in catalog, got {len(catalog)}"
    # Sanity-check a known MCP exists with tools
    assert "mcp-auth" in catalog
    assert catalog["mcp-auth"]["tool_count"] > 0
