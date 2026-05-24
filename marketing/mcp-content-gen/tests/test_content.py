def test_no_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    from importlib import reload
    import src.server as s; reload(s)
    from src.server import _validate
    assert _validate() is not None
