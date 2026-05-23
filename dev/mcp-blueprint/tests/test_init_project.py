"""
test_init_project.py — Tests for init_project, check_spec_completeness,
and gate_pre_build.

Tests patch settings.data_dir to a temp directory so no real data is written.
Run with: uv run pytest tests/ -v
"""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_settings(tmp_path: Path):
    """Return a mock settings object pointing at tmp_path."""
    m = MagicMock()
    m.brand = "mmiri28 solutions"
    m.owner = "chaghadi"
    m.data_dir = tmp_path
    tmp_path.mkdir(parents=True, exist_ok=True)
    return m


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# init_project
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestInitProject:
    def test_creates_spec_and_audit(self, tmp_path):
        ms = _mock_settings(tmp_path)
        with patch("src.tools.init_project.settings", ms), \
             patch("src.tools.spec_io.settings", ms):
            from src.tools.init_project import run
            result = run(
                brief="A task management app for developers.",
                project_name="TaskFlow",
                stack="fullstack",
            )

        assert result["ok"] is True
        assert result["project_slug"] == "taskflow"
        assert result["brand"] == "mmiri28 solutions"
        assert result["stack"] == "fullstack"

        spec_path = tmp_path / "projects" / "taskflow" / "spec.json"
        assert spec_path.exists(), "spec.json should be created"

        spec = json.loads(spec_path.read_text())
        assert spec["project_name"] == "TaskFlow"
        assert spec["stack"] == "fullstack"
        assert spec["status"] == "draft"
        assert spec["brief"] == "A task management app for developers."
        assert spec["completeness_score"] == 5  # brief present

        audit_path = tmp_path / "projects" / "taskflow" / "audit.jsonl"
        assert audit_path.exists(), "audit.jsonl should be created"
        entries = [json.loads(l) for l in audit_path.read_text().splitlines() if l]
        assert len(entries) == 1
        assert entries[0]["action"] == "init_project"
        assert entries[0]["actor"] == "chaghadi"

    def test_slugifies_project_name(self, tmp_path):
        ms = _mock_settings(tmp_path)
        with patch("src.tools.init_project.settings", ms), \
             patch("src.tools.spec_io.settings", ms):
            from src.tools.init_project import run
            result = run(brief="Test.", project_name="My Cool App", stack="web")
        assert result["project_slug"] == "my-cool-app"

    def test_rejects_duplicate_project(self, tmp_path):
        ms = _mock_settings(tmp_path)
        with patch("src.tools.init_project.settings", ms), \
             patch("src.tools.spec_io.settings", ms):
            from src.tools.init_project import run
            run(brief="First.", project_name="DupApp", stack="web")
            result = run(brief="Second.", project_name="DupApp", stack="web")
        assert "error" in result
        assert "already exists" in result["error"]

    def test_rejects_invalid_stack(self, tmp_path):
        ms = _mock_settings(tmp_path)
        with patch("src.tools.init_project.settings", ms), \
             patch("src.tools.spec_io.settings", ms):
            from src.tools.init_project import run
            result = run(brief="Test.", project_name="App", stack="desktop")
        assert "error" in result
        assert "Invalid stack" in result["error"]

    def test_rejects_empty_brief(self, tmp_path):
        ms = _mock_settings(tmp_path)
        with patch("src.tools.init_project.settings", ms), \
             patch("src.tools.spec_io.settings", ms):
            from src.tools.init_project import run
            result = run(brief="", project_name="App", stack="web")
        assert "error" in result

    def test_next_steps_present(self, tmp_path):
        ms = _mock_settings(tmp_path)
        with patch("src.tools.init_project.settings", ms), \
             patch("src.tools.spec_io.settings", ms):
            from src.tools.init_project import run
            result = run(brief="Test.", project_name="App", stack="web")
        assert "next_steps" in result
        assert len(result["next_steps"]) > 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# check_spec_completeness
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestCheckSpecCompleteness:
    def _init(self, tmp_path):
        ms = _mock_settings(tmp_path)
        with patch("src.tools.init_project.settings", ms), \
             patch("src.tools.spec_io.settings", ms):
            from src.tools.init_project import run
            run(brief="A test project.", project_name="ScoreTest", stack="web")
        return ms

    def test_score_with_only_brief(self, tmp_path):
        ms = self._init(tmp_path)
        with patch("src.tools.check_spec_completeness.settings", ms), \
             patch("src.tools.spec_io.settings", ms):
            from src.tools.check_spec_completeness import run
            result = run("scoretest")
        assert result["ok"] is True
        assert result["score"] == 5  # brief only
        assert result["build_ready"] is False

    def test_score_increases_with_prd(self, tmp_path):
        ms = self._init(tmp_path)
        # Manually write PRD into spec
        spec_path = tmp_path / "projects" / "scoretest" / "spec.json"
        spec = json.loads(spec_path.read_text())
        spec["prd"] = "# PRD\nOverview: ..."
        spec_path.write_text(json.dumps(spec, indent=2))

        with patch("src.tools.check_spec_completeness.settings", ms), \
             patch("src.tools.spec_io.settings", ms):
            from src.tools.check_spec_completeness import run
            result = run("scoretest")
        assert result["score"] == 25  # brief (5) + prd (20)

    def test_gaps_sorted_by_weight(self, tmp_path):
        ms = self._init(tmp_path)
        with patch("src.tools.check_spec_completeness.settings", ms), \
             patch("src.tools.spec_io.settings", ms):
            from src.tools.check_spec_completeness import run
            result = run("scoretest")
        gaps = result["gaps"]
        weights = [g["points"] for g in gaps]
        assert weights == sorted(weights, reverse=True), "gaps should be sorted by points desc"

    def test_error_on_missing_project(self, tmp_path):
        ms = _mock_settings(tmp_path)
        with patch("src.tools.check_spec_completeness.settings", ms), \
             patch("src.tools.spec_io.settings", ms):
            from src.tools.check_spec_completeness import run
            result = run("does-not-exist")
        assert "error" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# gate_pre_build
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestGatePreBuild:
    def _init(self, tmp_path):
        ms = _mock_settings(tmp_path)
        with patch("src.tools.init_project.settings", ms), \
             patch("src.tools.spec_io.settings", ms):
            from src.tools.init_project import run
            run(brief="A gated project.", project_name="GateTest", stack="fullstack")
        return ms

    def test_blocks_with_low_score(self, tmp_path):
        ms = self._init(tmp_path)
        with patch("src.tools.gate_pre_build.settings", ms), \
             patch("src.tools.spec_io.settings", ms):
            from src.tools.gate_pre_build import run
            result = run("gatetest")
        assert result["result"] == "block"
        assert len(result["blocks"]) > 0

    def test_passes_with_full_spec(self, tmp_path):
        ms = self._init(tmp_path)
        # Manually fill the spec to hit 85+
        spec_path = tmp_path / "projects" / "gatetest" / "spec.json"
        spec = json.loads(spec_path.read_text())
        spec["prd"] = "Full PRD"
        spec["tech_spec"] = "Full tech spec"
        spec["api_contracts"] = [{"path": "/health", "method": "GET"}]
        spec["schemas"] = [{"table": "users"}]
        spec["user_stories"] = [{"story": "As a user..."}]
        spec["design_tokens"] = {"color": {"primary": "#000"}}
        spec["components"] = [{"name": "Button"}]
        spec["wireframe_spec"] = "Screen: Home"
        spec["style_guide"] = "Typography: ..."
        spec["completeness_score"] = 100
        spec_path.write_text(json.dumps(spec, indent=2))

        with patch("src.tools.gate_pre_build.settings", ms), \
             patch("src.tools.spec_io.settings", ms):
            from src.tools.gate_pre_build import run
            result = run("gatetest")
        assert result["result"] == "pass"
        assert result["blocks"] == []

    def test_gate_result_written_to_audit(self, tmp_path):
        ms = self._init(tmp_path)
        with patch("src.tools.gate_pre_build.settings", ms), \
             patch("src.tools.spec_io.settings", ms):
            from src.tools.gate_pre_build import run
            run("gatetest")

        audit_path = tmp_path / "projects" / "gatetest" / "audit.jsonl"
        entries = [json.loads(l) for l in audit_path.read_text().splitlines() if l]
        gate_entries = [e for e in entries if e["action"] == "gate_pre_build"]
        assert len(gate_entries) == 1
        assert "result" in gate_entries[0]
