def test_invalid_decision(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost/x")
    from importlib import reload
    import src.config as c; reload(c)
    from src.server import complete_review
    result = complete_review("some-id", "bogus_decision")
    assert result["ok"] is False
