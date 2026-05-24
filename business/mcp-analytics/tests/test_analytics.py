"""test_analytics.py — Tests for mcp-analytics input validation."""

import pytest


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost/x")
    from importlib import reload
    import src.config as cfg
    reload(cfg)


class TestFunnelValidation:
    def test_funnel_requires_two_steps(self):
        from src.tools.analytics import run_get_funnel
        result = run_get_funnel("myapp", ["only_one_step"])
        assert result["ok"] is False
        assert "2" in result["error"]

    def test_funnel_accepts_two_steps(self):
        from unittest.mock import patch, MagicMock
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.__enter__ = MagicMock(return_value=mock_cur)
        mock_cur.__exit__ = MagicMock(return_value=False)
        mock_cur.fetchone.return_value = {"users": 100}
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor = MagicMock(return_value=mock_cur)

        with patch("src.tools.analytics.get_conn", return_value=mock_conn):
            from src.tools.analytics import run_get_funnel
            result = run_get_funnel("myapp", ["signup", "purchase"])
            assert result["ok"] is True
            assert len(result["funnel"]) == 2


class TestEventValidation:
    def test_get_events_limits_max(self):
        from unittest.mock import patch, MagicMock
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.__enter__ = MagicMock(return_value=mock_cur)
        mock_cur.__exit__ = MagicMock(return_value=False)
        mock_cur.fetchall.return_value = []
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor = MagicMock(return_value=mock_cur)

        with patch("src.tools.analytics.get_conn", return_value=mock_conn):
            from src.tools.analytics import run_get_events
            # Just check it doesn't crash with extreme limit
            result = run_get_events("app", limit=99999)
            assert result["ok"] is True
