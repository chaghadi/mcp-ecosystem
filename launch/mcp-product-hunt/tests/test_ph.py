def test_no_token(monkeypatch):
    monkeypatch.setenv("PRODUCT_HUNT_TOKEN", "")
    from importlib import reload
    import src.config as c; reload(c)
    from src.config import settings
    assert settings.validate() is not None
