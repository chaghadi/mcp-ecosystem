def test_no_api_key(monkeypatch):
    monkeypatch.setenv("COINBASE_COMMERCE_API_KEY", "")
    from importlib import reload
    import src.config as c; reload(c)
    from src.config import settings
    assert settings.validate() is not None

def test_webhook_verification_invalid_signature():
    import os
    os.environ["COINBASE_COMMERCE_API_KEY"] = "real-key"
    os.environ["COINBASE_WEBHOOK_SECRET"] = "test-secret"
    from importlib import reload
    import src.config as c; reload(c)
    from src.server import verify_webhook
    result = verify_webhook("payload", "wrong-sig")
    assert result["ok"] is True
    assert result["valid"] is False
