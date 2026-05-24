"""
test_redis.py — Tests for mcp-redis using fakeredis.

All tests run without a live Redis connection using fakeredis.
Live tests are skipped when REDIS_URL is not set.
"""

import os
import pytest
import fakeredis
from unittest.mock import patch

NEEDS_REDIS = pytest.mark.skipif(
    not os.environ.get("REDIS_URL"),
    reason="REDIS_URL not set — skipping live Redis tests.",
)


# ── Fake client fixture ───────────────────────────────────────────────────────

@pytest.fixture
def fake_client():
    """Return a fakeredis client that mimics real Redis."""
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    """Ensure key prefix is predictable in tests."""
    monkeypatch.setenv("KEY_PREFIX", "test")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379")
    # Reload settings with new env
    from importlib import reload
    import src.config as cfg
    reload(cfg)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Config
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestConfig:
    def test_validate_missing_url(self):
        from src.config import _Settings
        s = _Settings()
        s.redis_url = ""
        assert s.validate() is not None
        assert "REDIS_URL" in s.validate()

    def test_validate_wrong_scheme(self):
        from src.config import _Settings
        s = _Settings()
        s.redis_url = "postgresql://localhost"
        assert s.validate() is not None

    def test_validate_valid_url(self):
        from src.config import _Settings
        s = _Settings()
        s.redis_url = "redis://localhost:6379"
        assert s.validate() is None

    def test_prefixed_key(self):
        from src.config import _Settings
        s = _Settings()
        s.key_prefix = "myapp"
        assert s.prefixed("session:abc") == "myapp:session:abc"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Cache — using fakeredis
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestCache:
    def test_set_and_get(self, fake_client):
        with patch("src.tools.cache.get_client", return_value=fake_client):
            from src.tools.cache import run_set, run_get
            run_set("user:1", {"name": "Ada"})
            result = run_get("user:1")
            assert result["ok"] is True
            assert result["value"]["name"] == "Ada"

    def test_get_missing_key(self, fake_client):
        with patch("src.tools.cache.get_client", return_value=fake_client):
            from src.tools.cache import run_get
            result = run_get("does:not:exist")
            assert result["ok"] is True
            assert result["exists"] is False
            assert result["value"] is None

    def test_delete(self, fake_client):
        with patch("src.tools.cache.get_client", return_value=fake_client):
            from src.tools.cache import run_set, run_delete, run_exists
            run_set("to:delete", "value")
            run_delete("to:delete")
            result = run_exists("to:delete")
            assert result["exists"] is False

    def test_ttl(self, fake_client):
        with patch("src.tools.cache.get_client", return_value=fake_client):
            from src.tools.cache import run_set, run_ttl
            run_set("expiring", "val", ttl_seconds=60)
            result = run_ttl("expiring")
            assert result["ok"] is True
            assert result["ttl_seconds"] > 0

    def test_set_many_and_get_many(self, fake_client):
        with patch("src.tools.cache.get_client", return_value=fake_client):
            from src.tools.cache import run_set_many, run_get_many
            run_set_many({"a": 1, "b": 2, "c": 3})
            result = run_get_many(["a", "b", "c", "missing"])
            assert result["ok"] is True
            assert result["hit_count"] == 3
            assert result["miss_count"] == 1
            assert result["results"]["a"] == 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Queue — using fakeredis
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestQueue:
    def test_push_and_pop(self, fake_client):
        with patch("src.tools.queue.get_client", return_value=fake_client):
            from src.tools.queue import run_push, run_pop
            run_push("email", {"to": "ada@test.com"})
            result = run_pop("email")
            assert result["ok"] is True
            assert result["payload"]["to"] == "ada@test.com"
            assert result["empty"] is False

    def test_pop_empty_queue(self, fake_client):
        with patch("src.tools.queue.get_client", return_value=fake_client):
            from src.tools.queue import run_pop
            result = run_pop("empty_queue")
            assert result["ok"] is True
            assert result["empty"] is True
            assert result["payload"] is None

    def test_fifo_order(self, fake_client):
        with patch("src.tools.queue.get_client", return_value=fake_client):
            from src.tools.queue import run_push, run_pop
            run_push("order", {"seq": 1})
            run_push("order", {"seq": 2})
            run_push("order", {"seq": 3})
            first = run_pop("order")
            assert first["payload"]["seq"] == 1

    def test_length(self, fake_client):
        with patch("src.tools.queue.get_client", return_value=fake_client):
            from src.tools.queue import run_push, run_length
            run_push("len_test", "job1")
            run_push("len_test", "job2")
            result = run_length("len_test")
            assert result["length"] == 2

    def test_peek_does_not_consume(self, fake_client):
        with patch("src.tools.queue.get_client", return_value=fake_client):
            from src.tools.queue import run_push, run_peek, run_length
            run_push("peek_test", {"job": "a"})
            run_push("peek_test", {"job": "b"})
            run_peek("peek_test", count=10)
            length = run_length("peek_test")
            assert length["length"] == 2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Live Redis tests — skipped without REDIS_URL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestLiveRedis:
    @NEEDS_REDIS
    def test_health_check(self):
        from src.tools.health import run
        result = run()
        assert result["ok"] is True

    @NEEDS_REDIS
    def test_publish_returns_count(self):
        from src.tools.pubsub import run_publish
        result = run_publish("test.event", {"hello": "world"})
        assert result["ok"] is True
        assert "receiver_count" in result
