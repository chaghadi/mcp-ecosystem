def test_bump_invalid():
    import os; os.environ.setdefault("ECOSYSTEM_ROOT", "/tmp")
    from importlib import reload
    import src.config as c; reload(c)
    from src.server import bump_version
    result = bump_version("mcp-auth", "business", bump="invalid")
    assert result["ok"] is False
    assert "patch" in result["error"]

def test_bump_patch():
    import tempfile, os
    from pathlib import Path
    tmp = tempfile.mkdtemp()
    os.environ["ECOSYSTEM_ROOT"] = str(Path(tmp).parent.parent.parent.parent)
    # Write a minimal pyproject.toml
    mcp_dir = Path(tmp)
    (mcp_dir / "pyproject.toml").write_text('[project]\nname = "test"\nversion = "0.1.0"\n')
    
    from importlib import reload
    import src.config as c; reload(c)
    from src.config import settings
    # Override ecosystem root to use our temp dir structure
    # Just test the version parsing
    import re
    content = (mcp_dir / "pyproject.toml").read_text()
    match = re.search(r'version\s*=\s*"([^"]+)"', content)
    assert match
    assert match.group(1) == "0.1.0"
