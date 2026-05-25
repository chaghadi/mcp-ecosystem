"""main.py — mmiri hub for the mmiri28 MCP ecosystem.

Serves the banner page + a visual catalog of every MCP in the ecosystem.
Each MCP can be inspected (tool list) and pinged (live health check).
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.mcp_client import MCPClient
from src.catalog import discover_mcps

APP_SLUG = "mmiri"
STATIC_DIR = Path(__file__).parent / "static"

# Discover the ecosystem once on import
CATALOG = discover_mcps()

# Long-running MCP clients (only mcp-analytics for now)
analytics: MCPClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global analytics
    analytics = MCPClient("mcp-analytics", "business")
    try:
        await analytics.start()
        print("[mmiri] mcp-analytics session ready")
    except Exception as exc:
        print(f"[mmiri] WARNING: mcp-analytics did not start: {exc}")
        analytics = None
    yield
    if analytics:
        await analytics.stop()


app = FastAPI(
    title="mmiri",
    description="Visual hub for the mmiri28 MCP ecosystem",
    version="0.2.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def root(request: Request):
    """Hub page. Each visit recorded via mcp-analytics."""
    if analytics and analytics.is_connected:
        try:
            await analytics.call("track_event", {
                "app_slug": APP_SLUG,
                "event_name": "page_view",
                "properties": {"path": "/"},
            })
        except Exception as exc:
            print(f"[mmiri] track_event failed: {exc}")
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/mcps")
async def list_mcps():
    """Return the full ecosystem catalog."""
    return {"ok": True, **CATALOG}


@app.get("/api/mcp/{category}/{name}/health")
async def mcp_health(category: str, name: str):
    """Live health check for a specific MCP (spawns it briefly)."""
    if not name.startswith("mcp-"):
        return JSONResponse({"ok": False, "error": "invalid mcp name"}, status_code=400)

    # Quick path: just say "no analytics" without spawning anything
    client = MCPClient(name, category)
    try:
        await client.start()
        result = await client.call("health_check")
        await client.stop()
        return {"ok": True, "mcp": name, "category": category, "result": result}
    except Exception as exc:
        try:
            await client.stop()
        except Exception:
            pass
        return JSONResponse(
            {"ok": False, "mcp": name, "error": str(exc)[:300]},
            status_code=502,
        )


@app.get("/api/visit-count")
async def visit_count():
    """Total page_view events for this app."""
    if not analytics or not analytics.is_connected:
        return JSONResponse({"ok": False, "error": "mcp-analytics not connected"},
                            status_code=503)
    result = await analytics.call("get_event_counts", {"app_slug": APP_SLUG})
    if not result.get("ok"):
        return JSONResponse(result, status_code=502)
    counts = result.get("counts", [])
    page_views = next((c["count"] for c in counts if c.get("event_name") == "page_view"), 0)
    return {"ok": True, "page_views": page_views, "all_events": counts}


@app.get("/api/health")
async def health():
    """App-level health: confirms MCP layer is reachable."""
    if not analytics or not analytics.is_connected:
        return JSONResponse({"ok": False, "mcp_analytics": "disconnected"},
                            status_code=503)
    result = await analytics.call("health_check")
    return {
        "ok": True, "app": "mmiri",
        "mcp_analytics": "connected" if result.get("ok") else "error",
        "details": result,
        "catalog_totals": CATALOG["totals"],
    }


def run() -> None:
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8080, reload=False)


if __name__ == "__main__":
    run()
