import pytest
from pathlib import Path
from unittest.mock import patch

def test_read_env_file_skips_comments():
    from src.server import _read_env_file
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write("# comment\nKEY=value\nEMPTY=\n")
        name = f.name
    result = _read_env_file(Path(name))
    assert result["KEY"] == "value"
    assert "EMPTY" in result

def test_read_env_example():
    from src.server import _read_env_example
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env.example", delete=False) as f:
        f.write("# comment\nKEY=placeholder\nOTHER=value\n")
        name = f.name
    result = _read_env_example(Path(name))
    assert "KEY" in result
    assert "OTHER" in result
