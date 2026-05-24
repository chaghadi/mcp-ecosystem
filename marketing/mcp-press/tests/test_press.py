def test_no_db(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    from importlib import reload
    import src.config as c; reload(c)
    from src.config import settings
    assert settings.validate() is not None
