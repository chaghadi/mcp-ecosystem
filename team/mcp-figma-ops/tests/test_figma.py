def test_no_token(monkeypatch):
    monkeypatch.setenv("FIGMA_TOKEN", "")
    from importlib import reload
    import src.config as c; reload(c)
    from src.config import settings
    assert settings.validate() is not None

def test_invalid_export_format(monkeypatch):
    monkeypatch.setenv("FIGMA_TOKEN", "real-token")
    from importlib import reload
    import src.config as c; reload(c)
    from src.server import export_images
    result = export_images("filekey", ["1:2"], format="bmp")
    assert result["ok"] is False

def test_export_empty_nodes(monkeypatch):
    monkeypatch.setenv("FIGMA_TOKEN", "real-token")
    from importlib import reload
    import src.config as c; reload(c)
    from src.server import get_file_nodes
    result = get_file_nodes("filekey", [])
    assert result["ok"] is False
