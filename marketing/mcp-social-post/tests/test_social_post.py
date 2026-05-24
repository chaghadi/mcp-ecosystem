def test_twitter_not_configured(monkeypatch):
    monkeypatch.setenv("TWITTER_API_KEY", "")
    from importlib import reload
    import src.config as c; reload(c)
    from src.config import settings
    assert settings.validate_twitter() is not None
