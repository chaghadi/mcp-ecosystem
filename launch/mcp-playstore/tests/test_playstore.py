def test_no_credentials(monkeypatch):
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_PATH", "")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    from importlib import reload
    import src.config as c; reload(c)
    from src.config import settings
    assert settings.validate() is not None
