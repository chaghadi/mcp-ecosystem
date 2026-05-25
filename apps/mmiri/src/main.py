"""main.py — mmiri validation app.

A static banner page backed by real MCP calls.
Records each page view via mcp-analytics and shows the live count.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.mcp_client import MCPClient

APP_SLUG = "mmiri"
STATIC_DIR = Path(__file__).parent / "static"

# Module-level reference so route handlers can use it
analytics: MCPClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Spawn MCP clients on startup, tear them down on shutdown."""
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
        print("[mmiri] mcp-analytics session closed")


app = FastAPI(
    title="mmiri",
    description="Validation app for the mmiri28 MCP ecosystem",
    version="0.1.0",
    lifespan=lifespan,
)

# Static assets (CSS, etc.)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def root(request: Request):
    """Serve the banner page. Each visit is recorded via mcp-analytics."""
    if analytics and analytics.is_connected:
        try:
            await analytics.call("track_event", {
                "app_slug": APP_SLUG,
                "event_name": "page_view",
                "properties": {
                    "path": "/",
                    "user_agent": request.headers.get("user-agent", "")[:200],
                },
            })
        except Exception as exc:
            print(f"[mmiri] track_event failed: {exc}")
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/visit-count")
async def visit_count():
    """Return total page_view events for this app."""
    if not analytics or not analytics.is_connected:
        return JSONResponse({"ok": False, "error": "mcp-analytics not connected"},
                            status_code=503)
    result = await analytics.call("get_event_counts", {"app_slug": APP_SLUG})
    if not result.get("ok"):
        return JSONResponse(result, status_code=502)

    # Find the page_view count in the response
    counts = result.get("counts", [])
    page_views = next((c["count"] for c in counts if c.get("event_name") == "page_view"), 0)
    return {"ok": True, "page_views": page_views, "all_events": counts}


@app.get("/api/health")
async def health():
    """Health check — confirms the MCP layer is reachable."""
    if not analytics or not analytics.is_connected:
        return JSONResponse({"ok": False, "mcp_analytics": "disconnected"},
                            status_code=503)
    result = await analytics.call("health_check")
    return {
        "ok": True,
        "app": "mmiri",
        "mcp_analytics": "connected" if result.get("ok") else "error",
        "details": result,
    }


def run() -> None:
    """Entry point for `uv run mmiri`."""
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8080, reload=False)


if __name__ == "__main__":
    run()
