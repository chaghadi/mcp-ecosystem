"""
stubs.py — Placeholder implementations for tools not yet built.

All tools are registered in server.py so Claude Code can see the full
tool inventory. Stubs return a clear "not implemented" message with
a description of what the tool will do when built.

When implementing a stub, replace its call in server.py with the real module,
bump CHANGELOG.md, and update registry.json version.
"""

from typing import Any

_TOOL_DESCRIPTIONS = {
    # ── Phase 1: Specification ────────────────────────────────────────────────
    "write_prd": (
        "Generates a Product Requirements Document from the project brief. "
        "Outputs structured sections: overview, goals, non-goals, user personas, "
        "features (MoSCoW), success metrics, and open questions."
    ),
    "write_tech_spec": (
        "Derives the technical specification from the PRD. "
        "Outputs: system architecture, component breakdown, data flow, "
        "tech stack decisions, risks, and non-functional requirements."
    ),
    "define_api_contracts": (
        "Generates OpenAPI 3.0 contracts from the tech spec. "
        "Outputs endpoint definitions with request/response schemas, "
        "auth requirements, and error codes."
    ),
    "define_schema": (
        "Generates the database schema from the tech spec. "
        "Outputs table definitions with columns, types, indexes, "
        "and foreign key relationships."
    ),
    "write_user_stories": (
        "Generates epics and user stories from the PRD. "
        "Outputs GitHub Issues-compatible format with acceptance criteria."
    ),
    # ── Phase 2: Design ───────────────────────────────────────────────────────
    "generate_design_tokens": (
        "Generates design tokens (colors, typography, spacing, shadows) "
        "as tokens.json for React/Vite apps. Derived from brand identity."
    ),
    "define_components": (
        "Generates component inventory with props, states, and mapped API endpoints. "
        "Output feeds both Figma and the frontend scaffold."
    ),
    "write_wireframe_spec": (
        "Generates structured screen descriptions from the component inventory. "
        "Human-readable format that feeds Figma via mcp-figma-ops."
    ),
    "generate_style_guide": (
        "Generates the living style guide from design tokens and components. "
        "Outputs a Markdown document with usage rules."
    ),
    "push_tokens_to_figma": (
        "Pushes design tokens to Figma via mcp-figma-ops. "
        "Requires mcp-figma-ops to be active and connected."
    ),
    # ── Phase 3: Gates ────────────────────────────────────────────────────────
    "gate_pre_deploy": (
        "Validates implementation matches spec before mcp-vercel / mcp-digitalocean "
        "can deploy. Returns 'pass', 'warn', or 'block'."
    ),
    "diff_spec": (
        "Compares two spec versions and outputs a structured diff. "
        "Used by generate_release_doc and gate_pre_deploy."
    ),
    "generate_release_doc": (
        "Assembles a release document from spec diff, user stories, and API changes. "
        "Written to data/projects/{slug}/releases/."
    ),
}


def not_implemented(tool_name: str, project_slug: str | None = None) -> dict[str, Any]:
    """Return a standard not-implemented response for stub tools."""
    description = _TOOL_DESCRIPTIONS.get(tool_name, "No description available.")
    return {
        "ok": False,
        "status": "not_implemented",
        "tool": tool_name,
        "project_slug": project_slug,
        "message": (
            f"'{tool_name}' is not yet implemented. "
            "It is registered so Claude Code can see it, but its logic has not been built yet."
        ),
        "will_do": description,
        "next": (
            f"To implement this tool: "
            f"create dev/mcp-blueprint/src/tools/{tool_name}.py, "
            f"replace the stub call in server.py, "
            f"bump CHANGELOG.md and registry.json version."
        ),
    }
