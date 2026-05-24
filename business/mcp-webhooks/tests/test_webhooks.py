"""test_webhooks.py — Tests for mcp-webhooks signature verification and validation."""

import hashlib
import hmac
import json
import pytest


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost/x")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379")
    from importlib import reload
    import src.config as cfg
    reload(cfg)


class TestSignatureVerification:
    def test_valid_signature(self):
        from src.tools.webhooks import run_verify_signature
        secret = "test-secret-key"
        payload = json.dumps({"event": "payment.completed", "amount": 10000})
        signature = "sha256=" + hmac.new(
            secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        result = run_verify_signature(payload, signature, secret)
        assert result["ok"] is True
        assert result["valid"] is True

    def test_invalid_signature(self):
        from src.tools.webhooks import run_verify_signature
        result = run_verify_signature(
            '{"event": "test"}', "sha256=invalid", "secret"
        )
        assert result["ok"] is True
        assert result["valid"] is False


class TestWebhookValidation:
    def test_register_rejects_http_url(self):
        from unittest.mock import patch
        with patch("src.tools.webhooks.get_conn"):
            from src.tools.webhooks import run_register_webhook
            result = run_register_webhook(
                "http://example.com/webhook", ["payment.completed"], "myapp"
            )
            assert result["ok"] is False
            assert "HTTPS" in result["error"]

    def test_register_rejects_empty_events(self):
        from unittest.mock import patch
        with patch("src.tools.webhooks.get_conn"):
            from src.tools.webhooks import run_register_webhook
            result = run_register_webhook(
                "https://example.com/webhook", [], "myapp"
            )
            assert result["ok"] is False
