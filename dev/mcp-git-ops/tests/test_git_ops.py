import pytest

def test_validate_missing_token(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "")
    from importlib import reload
    import src.config as c; reload(c)
    from src.config import settings
    assert settings.validate() is not None

def test_validate_configured(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_realtoken123")
    from importlib import reload
    import src.config as c; reload(c)
    from src.config import settings
    assert settings.validate() is None
