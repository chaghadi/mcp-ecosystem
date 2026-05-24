def test_sitemap_empty():
    from src.server import generate_sitemap
    result = generate_sitemap([])
    assert result["ok"] is False

def test_sitemap_basic():
    from src.server import generate_sitemap
    result = generate_sitemap([{"loc": "https://example.com/", "priority": 1.0}])
    assert result["ok"] is True
    assert "<loc>https://example.com/</loc>" in result["sitemap_xml"]
