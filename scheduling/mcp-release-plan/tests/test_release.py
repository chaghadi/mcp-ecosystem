def test_invalid_status(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost/x")
    from importlib import reload
    import src.config as c; reload(c)
    from src.server import update_status
    result = update_status("some-id", "invalid_status")
    assert result["ok"] is False
