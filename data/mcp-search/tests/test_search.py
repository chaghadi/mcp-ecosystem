import pytest

def test_short_query():
    from unittest.mock import patch
    import os; os.environ["DATABASE_URL"] = "postgresql://x:x@localhost/x"
    from importlib import reload
    import src.config as c; reload(c)
    from src.tools.search_tools import run_search
    result = run_search("a", "myapp")
    assert result["ok"] is False
    assert "2 characters" in result["error"]

def test_empty_content():
    from unittest.mock import patch
    import os; os.environ["DATABASE_URL"] = "postgresql://x:x@localhost/x"
    from importlib import reload
    import src.config as c; reload(c)
    from src.tools.search_tools import run_index
    result = run_index("doc1", "", "myapp")
    assert result["ok"] is False
