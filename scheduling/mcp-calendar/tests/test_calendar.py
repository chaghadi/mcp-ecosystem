def test_validate_no_token(monkeypatch):
    monkeypatch.setenv("GOOGLE_REFRESH_TOKEN", "")
    from importlib import reload
    import src.config as c; reload(c)
    from src.config import settings
    assert settings.validate() is not None
