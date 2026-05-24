"""
test_postgres.py — Tests for mcp-postgres tools.

Tests that don't need a live database run unconditionally.
Tests that require a connection are skipped when DATABASE_URL is not set.
"""

import os
import pytest

NEEDS_DB = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set — skipping live database tests.",
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Config — no DB needed
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestConfig:
    def test_validate_missing_url(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        # Re-import to get a fresh settings with empty URL
        from importlib import reload
        import src.config as cfg_module
        reload(cfg_module)
        from src.config import _Settings
        s = _Settings()
        s.database_url = ""
        error = s.validate()
        assert error is not None
        assert "DATABASE_URL" in error

    def test_validate_bad_url(self):
        from src.config import _Settings
        s = _Settings()
        s.database_url = "mysql://user:pass@host/db"
        error = s.validate()
        assert error is not None
        assert "postgresql" in error.lower() or "PostgreSQL" in error

    def test_validate_good_url(self):
        from src.config import _Settings
        s = _Settings()
        s.database_url = "postgresql://user:pass@localhost:5432/mydb"
        assert s.validate() is None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Migration name validation — no DB needed
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestMigrateValidation:
    def test_create_migration_rejects_empty_name(self):
        from src.tools.migrate import run_create_migration
        result = run_create_migration("")
        assert "error" in result

    def test_create_migration_rejects_whitespace(self):
        from src.tools.migrate import run_create_migration
        result = run_create_migration("   ")
        assert "error" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Query validation — no DB needed
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestQueryValidation:
    def test_query_rejects_empty_sql(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost/x")
        from src.tools.query import run_query
        result = run_query("")
        assert "error" in result

    def test_execute_rejects_empty_sql(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost/x")
        from src.tools.query import run_execute
        result = run_execute("")
        assert "error" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Live DB tests — skipped without DATABASE_URL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestLiveDB:
    @NEEDS_DB
    def test_health_check_passes(self):
        from src.tools.health import run
        result = run()
        assert result["ok"] is True
        assert "version" in result

    @NEEDS_DB
    def test_query_select_one(self):
        from src.tools.query import run_query
        result = run_query("SELECT 1 AS val")
        assert result["ok"] is True
        assert result["rows"][0]["val"] == 1

    @NEEDS_DB
    def test_list_tables_returns_list(self):
        from src.tools.schema import run_list_tables
        result = run_list_tables("public")
        assert result["ok"] is True
        assert isinstance(result["tables"], list)

    @NEEDS_DB
    def test_migrate_status_returns_revision(self):
        from src.tools.migrate import run_migrate_status
        result = run_migrate_status()
        assert result["ok"] is True
        assert "current_revision" in result
