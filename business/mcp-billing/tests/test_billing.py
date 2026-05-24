"""test_billing.py — Tests for mcp-billing config and provider routing."""

import pytest


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost/x")
    monkeypatch.setenv("DEFAULT_CURRENCY", "USD")
    from importlib import reload
    import src.config as cfg
    reload(cfg)


class TestProviderRouting:
    def test_ngn_routes_to_paystack(self):
        from src.config import settings
        assert settings.provider_for("NGN") == "paystack"

    def test_ghs_routes_to_paystack(self):
        from src.config import settings
        assert settings.provider_for("GHS") == "paystack"

    def test_usd_routes_to_stripe(self):
        from src.config import settings
        assert settings.provider_for("USD") == "stripe"

    def test_eur_routes_to_stripe(self):
        from src.config import settings
        assert settings.provider_for("EUR") == "stripe"

    def test_explicit_override(self):
        from src.config import settings
        assert settings.provider_for("USD", "paystack") == "paystack"
        assert settings.provider_for("NGN", "stripe") == "stripe"

    def test_unconfigured_stripe_returns_error(self, monkeypatch):
        monkeypatch.setenv("STRIPE_SECRET_KEY", "")
        from importlib import reload
        import src.config as cfg
        reload(cfg)
        from src.config import settings
        assert settings.validate_stripe() is not None

    def test_unconfigured_paystack_returns_error(self, monkeypatch):
        monkeypatch.setenv("PAYSTACK_SECRET_KEY", "")
        from importlib import reload
        import src.config as cfg
        reload(cfg)
        from src.config import settings
        assert settings.validate_paystack() is not None
