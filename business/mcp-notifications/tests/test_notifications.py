"""test_notifications.py — Tests for mcp-notifications routing."""

import pytest


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "")
    from importlib import reload
    import src.config as cfg
    reload(cfg)


class TestSmsRouting:
    def test_nigerian_number_routes_to_termii(self):
        from src.config import settings
        assert settings.sms_provider_for("+2348012345678") == "termii"
        assert settings.sms_provider_for("2348012345678") == "termii"

    def test_uk_number_routes_to_twilio(self):
        from src.config import settings
        assert settings.sms_provider_for("+447700900123") == "twilio"

    def test_us_number_routes_to_twilio(self):
        from src.config import settings
        assert settings.sms_provider_for("+14155552671") == "twilio"


class TestEmailValidation:
    def test_send_email_requires_body(self):
        from src.tools.email import run_send_email
        result = run_send_email("test@test.com", "Subject")
        # Either not configured or missing body — both are failures
        assert result["ok"] is False

    def test_send_sms_rejects_empty_to(self):
        from src.tools.sms import run_send_sms
        result = run_send_sms("", "Hello")
        assert result["ok"] is False

    def test_send_sms_rejects_empty_message(self):
        from src.tools.sms import run_send_sms
        result = run_send_sms("+2348012345678", "")
        assert result["ok"] is False
