def test_invalid_domain():
    from src.server import check_ssl
    result = check_ssl("definitely-not-a-real-domain-xyz-12345.example")
    assert result["ok"] is False
