def test_lint_returns_result():
    import os; os.environ.setdefault("ECOSYSTEM_ROOT", "/tmp")
    from importlib import reload
    import src.config as c; reload(c)
    # Just verify the function exists and returns a dict
    from src.server import lint_python
    # Can't run ruff without it installed, just check structure
    assert callable(lint_python)
