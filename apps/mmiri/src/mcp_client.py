"""mcp_client.py — manages persistent stdio connections to MCPs.

The app spawns each MCP as a subprocess on startup, keeps the JSON-RPC
session alive for the lifetime of the app, and tears it down on shutdown.

This matches the runtime architecture from the ecosystem docs:
    App ──MCP protocol──> MCP server ──> external service

The app never holds external service credentials. Only the MCPs do.
"""

import json
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# Resolve the mcp-ecosystem repo root (apps/mmiri/src/mcp_client.py -> repo root)
ECOSYSTEM_ROOT = Path(__file__).resolve().parents[3]


class MCPClient:
    """Persistent client for a single MCP server.

    Use via `await client.start()` and `await client.stop()`,
    or inside a FastAPI lifespan handler.
    """

    def __init__(self, mcp_name: str, category: str):
        self.mcp_name = mcp_name
        self.cwd = ECOSYSTEM_ROOT / category / mcp_name
        self._session: ClientSession | None = None
        self._stack: AsyncExitStack | None = None

    async def start(self) -> None:
        """Spawn the MCP subprocess and open a JSON-RPC session."""
        if not self.cwd.exists():
            raise FileNotFoundError(f"MCP not found at {self.cwd}")

        params = StdioServerParameters(
            command="uv", args=["run", self.mcp_name],
            cwd=str(self.cwd),
        )

        self._stack = AsyncExitStack()
        read, write = await self._stack.enter_async_context(stdio_client(params))
        self._session = await self._stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()

    async def stop(self) -> None:
        """Tear down the session and subprocess cleanly."""
        if self._stack:
            await self._stack.aclose()
        self._session = None
        self._stack = None

    async def call(self, tool: str, args: dict | None = None) -> dict[str, Any]:
        """Call an MCP tool and return its result as a dict.

        MCP tool responses arrive as content blocks; we extract the first
        text block and JSON-parse it (the convention our MCPs follow).
        """
        if not self._session:
            raise RuntimeError(f"{self.mcp_name} session not started.")

        result = await self._session.call_tool(tool, args or {})
        for block in result.content:
            if hasattr(block, "text"):
                try:
                    return json.loads(block.text)
                except json.JSONDecodeError:
                    return {"ok": True, "raw": block.text}
        return {"ok": False, "error": "empty MCP response"}

    @property
    def is_connected(self) -> bool:
        return self._session is not None
