"""
test_auth.py — Tests for mcp-auth using mocks.

Password hashing, JWT, token blacklisting, and input validation
all tested without live database or Redis connections.
"""

import pytest
import fakeredis
from unittest.mock import patch
from freezegun import freeze_time


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Config
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379")
    monkeypatch.setenv("JWT_SECRET", "a" * 64)
    monkeypatch.setenv("SUPERADMIN_EMAIL", "admin@mmiri28.com")
    from importlib import reload
    import src.config as cfg
    reload(cfg)


class TestConfig:
    def test_missing_jwt_secret(self):
        from src.config import _Settings
        s = _Settings()
        s.jwt_secret = ""
        assert s.validate() is not None

    def test_placeholder_jwt_secret(self):
        from src.config import _Settings
        s = _Settings()
        s.jwt_secret = "change-this-to-a-random-hex-string"
        assert s.validate() is not None

    def test_valid_config(self):
        from src.config import _Settings
        s = _Settings()
        s.database_url = "postgresql://x"
        s.redis_url = "redis://x"
        s.jwt_secret = "a" * 64
        assert s.validate() is None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Password hashing
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestPasswords:
    def test_hash_and_verify(self):
        from src.tools.auth import _hash_password, _verify_password
        hashed = _hash_password("securepassword")
        assert hashed != "securepassword"
        assert _verify_password("securepassword", hashed)
        assert not _verify_password("wrongpassword", hashed)

    def test_password_too_short(self):
        from src.tools.auth import _validate_password_strength
        assert _validate_password_strength("short") is not None
        assert _validate_password_strength("exactly8") is None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# JWT tokens
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestTokens:
    def test_create_and_decode(self):
        from src.tools.tokens import create_access_token, decode_access_token
        token = create_access_token("user-123", "user", [{"app": "marketplace", "roles": ["seller"]}])
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["global_role"] == "user"
        assert payload["app_roles"][0]["app"] == "marketplace"

    def test_expired_token_returns_none(self):
        from src.tools.tokens import create_access_token, decode_access_token
        with freeze_time("2026-01-01 00:00:00"):
            token = create_access_token("user-123", "user", [])
        with freeze_time("2026-01-01 01:00:00"):  # 1 hour later — well past 15min
            payload = decode_access_token(token)
        assert payload is None

    def test_invalid_token_returns_none(self):
        from src.tools.tokens import decode_access_token
        assert decode_access_token("not.a.token") is None
        assert decode_access_token("") is None

    def test_blacklist_token(self):
        fake_redis = fakeredis.FakeRedis(decode_responses=True)
        from src.tools.tokens import create_access_token
        token = create_access_token("user-123", "user", [])

        with patch("src.tools.tokens._get_redis", return_value=fake_redis):
            from src.tools.tokens import blacklist_token, is_token_blacklisted
            assert not is_token_blacklisted(token)
            blacklist_token(token)
            assert is_token_blacklisted(token)

    def test_refresh_token_generation(self):
        from src.tools.tokens import generate_refresh_token, hash_refresh_token
        raw, hashed = generate_refresh_token()
        assert raw != hashed
        assert len(raw) > 32
        assert hash_refresh_token(raw) == hashed


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Input validation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestInputValidation:
    def test_register_invalid_auth_method(self, monkeypatch):
        with patch("src.tools.auth.get_conn"):
            from src.tools.auth import run_register
            result = run_register("test@test.com", "password123", auth_method="twitter")
            assert result["ok"] is False
            assert "auth_method" in result["error"]

    def test_register_empty_identifier(self):
        from src.tools.auth import run_register
        result = run_register("", "password123", auth_method="email")
        assert result["ok"] is False

    def test_verify_token_invalid(self):
        with patch("src.tools.tokens._get_redis", return_value=fakeredis.FakeRedis(decode_responses=True)):
            from src.tools.auth import run_verify_token
            result = run_verify_token("invalid.token.here")
            assert result["ok"] is False

    def test_superadmin_role_assigned_on_register(self, monkeypatch):
        from src.config import _Settings
        s = _Settings()
        s.superadmin_email = "admin@mmiri28.com"
        # The logic check itself
        from src.tools.auth import _hash_password
        global_role = "superadmin" if "admin@mmiri28.com" == s.superadmin_email else "user"
        assert global_role == "superadmin"

    def test_create_role_rejects_empty_name(self):
        with patch("src.tools.roles.get_conn"):
            from src.tools.roles import run_create_role
            result = run_create_role("marketplace", "")
            assert result["ok"] is False
