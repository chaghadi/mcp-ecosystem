def test_validate_missing_token(monkeypatch):
    monkeypatch.setenv("VERCEL_TOKEN", "")
    from importlib import reload
    import src.config as c; reload(c)
    from src.config import settings
    assert settings.validate() is not None
