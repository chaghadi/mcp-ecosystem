def test_no_db(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    from importlib import reload
    import src.config as c; reload(c)
    from src.config import settings
    assert settings.validate() is not None

def test_empty_steps(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost/x")
    from importlib import reload
    import src.config as c; reload(c)
    from src.server import create_template
    result = create_template("test", "app", "engineer", steps=[])
    assert result["ok"] is False
