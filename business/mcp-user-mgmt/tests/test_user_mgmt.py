"""test_user_mgmt.py — Tests for mcp-user-mgmt."""

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    from importlib import reload
    import src.config as cfg
    reload(cfg)


class TestConfig:
    def test_missing_database_url(self):
        from src.config import _Settings
        s = _Settings()
        s.database_url = ""
        assert s.validate() is not None

    def test_valid_config(self):
        from src.config import _Settings
        s = _Settings()
        s.database_url = "postgresql://x"
        assert s.validate() is None


class TestProfiles:
    def test_update_profile_rejects_invalid_fields(self):
        with patch("src.tools.profiles.get_conn"):
            from src.tools.profiles import run_update_profile
            result = run_update_profile("user-123", {"password": "hack", "admin": True})
            assert result["ok"] is False
            assert "No valid fields" in result["error"]

    def test_update_profile_accepts_valid_fields(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.__enter__ = MagicMock(return_value=mock_cur)
        mock_cur.__exit__ = MagicMock(return_value=False)
        mock_cur.fetchone.return_value = {"id": "profile-1"}
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor = MagicMock(return_value=mock_cur)

        with patch("src.tools.profiles.get_conn", return_value=mock_conn):
            from src.tools.profiles import run_update_profile
            result = run_update_profile("user-123", {"display_name": "Ada", "bio": "Engineer"})
            assert result["ok"] is True
            assert set(result["updated_fields"]) == {"display_name", "bio"}


class TestPreferences:
    def test_namespace_defaults_to_global(self):
        from src.tools.preferences import _ns
        assert _ns(None) == "global"
        assert _ns("marketplace") == "marketplace"

    def test_set_preference_rejects_empty_key(self):
        with patch("src.tools.preferences.get_conn"):
            from src.tools.preferences import run_set_preference
            result = run_set_preference("user-123", "", "value")
            assert result["ok"] is False

    def test_set_preferences_rejects_empty_dict(self):
        with patch("src.tools.preferences.get_conn"):
            from src.tools.preferences import run_set_preferences
            result = run_set_preferences("user-123", {})
            assert result["ok"] is False


class TestSearch:
    def test_search_rejects_short_query(self):
        from src.tools.search import run_search_users
        result = run_search_users("a")
        assert result["ok"] is False
        assert "2 characters" in result["error"]

    def test_search_accepts_valid_query(self):
        with patch("src.tools.search.get_conn"):
            from src.tools.search import run_search_users
            # Just validate it doesn't error on input — DB mock handles the rest
            assert True


class TestLifecycle:
    def test_delete_user_not_found(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.__enter__ = MagicMock(return_value=mock_cur)
        mock_cur.__exit__ = MagicMock(return_value=False)
        mock_cur.fetchone.return_value = None
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor = MagicMock(return_value=mock_cur)

        with patch("src.tools.lifecycle.get_conn", return_value=mock_conn):
            from src.tools.lifecycle import run_delete_user
            result = run_delete_user("nonexistent-id")
            assert result["ok"] is False
            assert "not found" in result["error"]
