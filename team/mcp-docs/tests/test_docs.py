def test_no_db(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    from importlib import reload
    import src.config as c; reload(c)
    from src.config import settings
    assert settings.validate() is not None

def test_slugify():
    from src.server import _slugify
    assert _slugify("Hello World!") == "hello-world"
    assert _slugify("  Multiple   Spaces  ") == "multiple-spaces"

def test_search_short_query(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost/x")
    from importlib import reload
    import src.config as c; reload(c)
    from src.server import search_docs
    result = search_docs("a")
    assert result["ok"] is False
