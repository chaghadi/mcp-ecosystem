# mcp-blueprint

**Version:** 0.1.0
**Runtime:** Python 3.11+
**Transport:** stdio
**Brand:** mmiri28 solutions

Spec-and-gate MCP. Owns the full project lifecycle from brief to deploy.
**Nothing gets built or shipped without passing through it.**

---

## What it does

`mcp-blueprint` has three phases:

### Phase 1 — Specification
| Tool | Status | Points | Description |
|------|--------|--------|-------------|
| `init_project` | ✅ built | — | Initialize spec from brief |
| `write_prd` | 🔲 stub | 20 | Product Requirements Document |
| `write_tech_spec` | 🔲 stub | 15 | Technical specification |
| `define_api_contracts` | 🔲 stub | 15 | OpenAPI 3.0 contracts |
| `define_schema` | 🔲 stub | 10 | Database schema |
| `write_user_stories` | 🔲 stub | 10 | Epics and stories |
| `check_spec_completeness` | ✅ built | — | Score 0-100, gap report |

### Phase 2 — Design
| Tool | Status | Points | Description |
|------|--------|--------|-------------|
| `generate_design_tokens` | 🔲 stub | 10 | tokens.json for React/Vite |
| `define_components` | 🔲 stub | 10 | Component inventory |
| `write_wireframe_spec` | 🔲 stub | 3 | Screen descriptions → Figma |
| `generate_style_guide` | 🔲 stub | 2 | Living style guide |
| `push_tokens_to_figma` | 🔲 stub | — | Push tokens via mcp-figma-ops |

### Phase 3 — Gates & Audit
| Tool | Status | Description |
|------|--------|-------------|
| `gate_pre_build` | ✅ built | Pass/block before mcp-scaffold runs |
| `gate_pre_deploy` | 🔲 stub | Pass/warn/block before deploy |
| `diff_spec` | 🔲 stub | Compare spec versions |
| `generate_release_doc` | 🔲 stub | Assemble release document |
| `get_audit_trail` | ✅ built | Full project history |
| `list_projects` | ✅ built | All initialized projects |

---

## Gate logic

**`gate_pre_build`** requires:
- Completeness score ≥ 85/100
- PRD written
- Tech spec written

**`gate_pre_deploy`** requires (once built):
- `gate_pre_build` previously passed
- Implementation matches API contracts

---

## Setup

From the `mcp-blueprint` directory:

```powershell
uv sync
copy .env.example .env
uv run pytest tests/ -v
uv run mcp-blueprint
```

---

## Data

Project specs and audit logs are stored in `data/projects/{slug}/`.
This directory is git-ignored. Back it up separately.

```
data/projects/{slug}/
├── spec.json      # the living project spec
└── audit.jsonl    # append-only action log
```

---

## Implementing a stub

1. Create `src/tools/{tool_name}.py` with a `run(...)` function
2. In `server.py`, replace `not_implemented("tool_name", ...)` with `tool_name.run(...)`
3. Import the module at the top of `server.py`
4. Write tests in `tests/`
5. Bump `version` in `pyproject.toml` (follow semver — see ADR-0001)
6. Add a `CHANGELOG.md` entry
7. Update `registry.json` in the ecosystem root

---

## Dependencies

```
mcp[cli]>=1.0.0
pydantic>=2.0.0
python-dotenv>=1.0.0
```

No external services required. Runs entirely as a local stdio process.
