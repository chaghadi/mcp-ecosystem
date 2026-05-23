# mcp-blueprint Changelog

All notable changes to this MCP are documented here.
Format: [version] — date — author — what changed and why.

---

## [0.1.0] — 2026-05-23 — chaghadi

**Initial build. mmiri28 solutions.**

### Added
- `init_project` — initialize a project spec from a plain-language brief.
  Creates `data/projects/{slug}/spec.json` and starts the audit trail.
- `check_spec_completeness` — score a spec 0-100. Returns gaps ranked by point value.
  Build gate requires 85+.
- `gate_pre_build` — validate a project is ready to build. Returns `pass` or `block`.
  Result is written to the audit trail. mcp-scaffold must not run until this passes.
- `get_audit_trail` — return the full audit trail for a project (append-only JSONL).
- `list_projects` — list all initialized projects and their last recorded action.

### Registered as stubs (not yet implemented)
Phase 1: `write_prd`, `write_tech_spec`, `define_api_contracts`,
         `define_schema`, `write_user_stories`
Phase 2: `generate_design_tokens`, `define_components`, `write_wireframe_spec`,
         `generate_style_guide`, `push_tokens_to_figma`
Phase 3: `gate_pre_deploy`, `diff_spec`, `generate_release_doc`

### Architecture decisions recorded
- ADR-0001: MCP Versioning Contract
- ADR-0002: mcp-blueprint Gates All Builds and Deployments

---

<!-- When adding a new version, copy the template below:

## [X.Y.Z] — YYYY-MM-DD — author

### Added
-

### Changed
-

### Fixed
-

### Breaking
- (MAJOR version bumps only — list what broke and migration path)

-->
