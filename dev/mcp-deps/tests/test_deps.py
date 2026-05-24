def test_missing_mcp():
    import os; os.environ.setdefault("ECOSYSTEM_ROOT", "/tmp")
    from importlib import reload
    import src.config as c; reload(c)
    from src.server import check_outdated
    result = check_outdated("nonexistent-mcp", "dev")
    assert result["ok"] is False
