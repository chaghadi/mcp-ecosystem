def test_no_credentials(monkeypatch):
    monkeypatch.setenv("APPSTORE_KEY_ID", "")
    monkeypatch.setenv("APPSTORE_ISSUER_ID", "")
    monkeypatch.setenv("APPSTORE_PRIVATE_KEY_PATH", "")
    monkeypatch.setenv("APPSTORE_PRIVATE_KEY", "")
    from importlib import reload
    import src.config as c; reload(c)
    from src.config import settings
    assert settings.validate() is not None
