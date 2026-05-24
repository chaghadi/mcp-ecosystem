"""
server.py — mcp-blueprint MCP server entry point.

All tools are registered here. Phase 1 (spec) and core Phase 3 (gates, audit)
are fully implemented. Phase 2 (design) and remaining Phase 3 tools are stubs
— they are registered so Claude Code can see the full tool inventory, but they
return "not implemented" until built.

Build order when implementing stubs:
  Phase 1: write_prd → write_tech_spec → define_api_contracts
           → define_schema → write_user_stories
  Phase 2: generate_design_tokens → define_components
           → write_wireframe_spec → generate_style_guide → push_tokens_to_figma
  Phase 3: gate_pre_deploy → diff_spec → generate_release_doc
"""

from mcp.server.fastmcp import FastMCP

from src.tools import audit_trail as _audit_trail
from src.tools import check_spec_completeness as _check_spec
from src.tools import gate_pre_build as _gate_pre_build
from src.tools import init_project as _init_project
from src.tools.stubs import not_implemented

mcp = FastMCP(
    "mcp-blueprint",
    instructions=(
        "Spec-and-gate MCP for mmiri28 solutions. "
        "Owns project lifecycle: brief → spec → design → gate → build → deploy. "
        "Nothing gets built or shipped without passing through it."
    ),
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Phase 1 — Specification
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@mcp.tool()
def init_project(brief: str, project_name: str, stack: str = "fullstack") -> dict:
    """
    Initialize a new project spec from a plain-language brief.

    Creates data/projects/{slug}/spec.json and starts the audit trail.
    Must be called before any other mcp-blueprint tool for a project.

    Args:
        brief:        One paragraph describing what you're building.
        project_name: Human-readable name, e.g. "TaskFlow". Used to derive the slug.
        stack:        "web" | "backend" | "mobile" | "fullstack"
    """
    return _init_project.run(brief=brief, project_name=project_name, stack=stack)


@mcp.tool()
def write_prd(project_slug: str) -> dict:
    """
    [STUB] Generate a Product Requirements Document from the project brief.

    Produces: overview, goals, non-goals, user personas, features (MoSCoW),
    success metrics, open questions. Adds 20 points to completeness score.
    """
    return not_implemented("write_prd", project_slug)


@mcp.tool()
def write_tech_spec(project_slug: str) -> dict:
    """
    [STUB] Derive the technical specification from the PRD.

    Produces: system architecture, component breakdown, data flow, tech stack
    decisions, risks, non-functional requirements. Adds 15 points.
    """
    return not_implemented("write_tech_spec", project_slug)


@mcp.tool()
def define_api_contracts(project_slug: str) -> dict:
    """
    [STUB] Generate OpenAPI 3.0 contracts from the tech spec.

    Produces endpoint definitions with request/response schemas, auth, error codes.
    Adds 15 points to completeness score.
    """
    return not_implemented("define_api_contracts", project_slug)


@mcp.tool()
def define_schema(project_slug: str) -> dict:
    """
    [STUB] Generate the database schema from the tech spec.

    Produces table definitions with columns, types, indexes, foreign keys.
    Adds 10 points to completeness score.
    """
    return not_implemented("define_schema", project_slug)


@mcp.tool()
def write_user_stories(project_slug: str) -> dict:
    """
    [STUB] Generate epics and user stories from the PRD.

    Produces GitHub Issues-compatible format with acceptance criteria.
    Adds 10 points to completeness score.
    """
    return not_implemented("write_user_stories", project_slug)


@mcp.tool()
def check_spec_completeness(project_slug: str) -> dict:
    """
    Score the completeness of a project spec (0-100).

    Checks every required section across Phase 1 (spec) and Phase 2 (design).
    Returns the score, a per-check breakdown, gaps ranked by point value,
    and the next recommended action. Build gate requires 85+.
    """
    return _check_spec.run(project_slug=project_slug)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Phase 2 — Design
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@mcp.tool()
def generate_design_tokens(project_slug: str) -> dict:
    """
    [STUB] Generate design tokens (colors, typography, spacing, shadows) as tokens.json.

    Output feeds React/Vite apps and Figma. Adds 10 points to completeness score.
    """
    return not_implemented("generate_design_tokens", project_slug)


@mcp.tool()
def define_components(project_slug: str) -> dict:
    """
    [STUB] Generate component inventory with props, states, and mapped API endpoints.

    Output feeds both Figma scaffold and frontend code generation. Adds 10 points.
    """
    return not_implemented("define_components", project_slug)


@mcp.tool()
def write_wireframe_spec(project_slug: str) -> dict:
    """
    [STUB] Generate structured screen descriptions from the component inventory.

    Human-readable format that feeds Figma via mcp-figma-ops. Adds 3 points.
    """
    return not_implemented("write_wireframe_spec", project_slug)


@mcp.tool()
def generate_style_guide(project_slug: str) -> dict:
    """
    [STUB] Generate the living style guide from design tokens and components.

    Adds 2 points to completeness score.
    """
    return not_implemented("generate_style_guide", project_slug)


@mcp.tool()
def push_tokens_to_figma(project_slug: str) -> dict:
    """
    [STUB] Push design tokens to Figma via mcp-figma-ops.

    Requires mcp-figma-ops to be active and a Figma API token configured.
    """
    return not_implemented("push_tokens_to_figma", project_slug)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Phase 3 — Gates & Audit
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@mcp.tool()
def gate_pre_build(project_slug: str) -> dict:
    """
    Validate a project is ready to be built.

    Returns 'pass' or 'block'. Requires completeness score ≥ 85, PRD written,
    and tech spec written. Result is written to the audit trail. mcp-scaffold
    must not run until this returns 'pass'.
    """
    return _gate_pre_build.run(project_slug=project_slug)


@mcp.tool()
def gate_pre_deploy(project_slug: str) -> dict:
    """
    [STUB] Validate implementation matches spec before deployment.

    Returns 'pass', 'warn', or 'block'. mcp-vercel and mcp-digitalocean
    must not deploy until this returns 'pass' or 'warn'.
    """
    return not_implemented("gate_pre_deploy", project_slug)


@mcp.tool()
def diff_spec(project_slug: str, version_a: str, version_b: str) -> dict:
    """
    [STUB] Compare two spec versions and output a structured diff.

    Used by generate_release_doc and gate_pre_deploy to detect
    breaking changes before building or deploying.
    """
    return not_implemented("diff_spec", project_slug)


@mcp.tool()
def generate_release_doc(project_slug: str) -> dict:
    """
    [STUB] Assemble a release document from spec diff, user stories, and API changes.

    Written to data/projects/{slug}/releases/. Used by mcp-changelog.
    """
    return not_implemented("generate_release_doc", project_slug)


@mcp.tool()
def get_audit_trail(project_slug: str) -> dict:
    """
    Return the full audit trail for a project.

    Shows every action taken: who, when, what result. Append-only log.
    Use this to understand the history of any project without asking anyone.
    """
    return _audit_trail.run(project_slug=project_slug)


@mcp.tool()
def list_projects() -> dict:
    """
    List all initialized projects and their last recorded action.
    """
    return _audit_trail.run_list_projects()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Entry point
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
