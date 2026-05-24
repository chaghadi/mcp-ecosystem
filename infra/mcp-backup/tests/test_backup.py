def test_no_credentials(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "")
    from importlib import reload
    import src.config as c; reload(c)
    from src.config import settings
    assert settings.validate() is not None
