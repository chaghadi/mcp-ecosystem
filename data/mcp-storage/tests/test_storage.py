"""
test_storage.py — Tests for mcp-storage using moto S3 mock.

moto intercepts boto3 calls and simulates S3/R2 in memory.
No live R2 credentials needed to run these tests.
"""

import os
import pytest
from unittest.mock import patch
from moto import mock_aws


TEST_BUCKET = "test-bucket"
TEST_ACCOUNT = "testaccountid"


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("R2_ACCOUNT_ID", TEST_ACCOUNT)
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "test-key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "test-secret")
    monkeypatch.setenv("R2_DEFAULT_BUCKET", TEST_BUCKET)
    monkeypatch.setenv("R2_PUBLIC_DOMAIN", "https://pub-test.r2.dev")
    from importlib import reload
    import src.config as cfg
    reload(cfg)


@pytest.fixture
def r2(tmp_path):
    """Start moto mock and create a test bucket."""
    with mock_aws():
        import boto3
        from src.config import settings

        # moto needs us to use us-east-1 for bucket creation in mock
        s3 = boto3.client(
            "s3",
            endpoint_url=None,  # use moto's mock endpoint
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret",
            region_name="us-east-1",
        )
        s3.create_bucket(Bucket=TEST_BUCKET)

        # Patch get_client to return a standard moto-mocked s3 client
        with patch("src.client.get_client", return_value=s3), \
             patch("src.tools.files.get_client", return_value=s3), \
             patch("src.tools.urls.get_client", return_value=s3), \
             patch("src.tools.health.check_connectivity",
                   return_value={"ok": True, "buckets": [TEST_BUCKET]}):
            yield s3, tmp_path


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Config
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestConfig:
    def test_validate_missing_credentials(self):
        from src.config import _Settings
        s = _Settings()
        s.account_id = ""
        assert s.validate() is not None

    def test_validate_valid(self):
        from src.config import _Settings
        s = _Settings()
        s.account_id = "abc"
        s.access_key_id = "key"
        s.secret_access_key = "secret"
        assert s.validate() is None

    def test_public_url(self):
        from src.config import _Settings
        s = _Settings()
        s.public_domain = "https://pub-test.r2.dev"
        assert s.public_url("logos/icon.png") == "https://pub-test.r2.dev/logos/icon.png"

    def test_public_url_none_when_no_domain(self):
        from src.config import _Settings
        s = _Settings()
        s.public_domain = ""
        assert s.public_url("any/key") is None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Files
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestFiles:
    def test_upload_and_download_text(self, r2):
        from src.tools.files import run_upload_text, run_download_text
        upload = run_upload_text("test/hello.txt", "Hello mmiri28", content_type="text/plain")
        assert upload["ok"] is True
        assert upload["size_bytes"] == len("Hello mmiri28".encode())

        download = run_download_text("test/hello.txt")
        assert download["ok"] is True
        assert download["content"] == "Hello mmiri28"

    def test_upload_file_not_found(self, r2):
        from src.tools.files import run_upload_file
        result = run_upload_file("test/missing.txt", "/nonexistent/path/file.txt")
        assert result["ok"] is False
        assert "not found" in result["error"]

    def test_file_exists_true(self, r2):
        from src.tools.files import run_upload_text, run_file_exists
        run_upload_text("exists/file.txt", "content")
        result = run_file_exists("exists/file.txt")
        assert result["ok"] is True
        assert result["exists"] is True

    def test_file_exists_false(self, r2):
        from src.tools.files import run_file_exists
        result = run_file_exists("does/not/exist.txt")
        assert result["ok"] is True
        assert result["exists"] is False

    def test_delete_file(self, r2):
        from src.tools.files import run_upload_text, run_delete_file, run_file_exists
        run_upload_text("to/delete.txt", "bye")
        run_delete_file("to/delete.txt")
        result = run_file_exists("to/delete.txt")
        assert result["exists"] is False

    def test_list_files(self, r2):
        from src.tools.files import run_upload_text, run_list_files
        run_upload_text("images/a.jpg", "img1")
        run_upload_text("images/b.jpg", "img2")
        run_upload_text("docs/c.pdf", "pdf1")
        result = run_list_files(prefix="images/")
        assert result["ok"] is True
        assert result["file_count"] == 2

    def test_public_url_in_upload(self, r2):
        from src.tools.files import run_upload_text
        result = run_upload_text("logos/icon.png", "fake-image-data")
        assert result["public_url"] == "https://pub-test.r2.dev/logos/icon.png"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# URLs
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestURLs:
    def test_get_public_url(self, r2):
        from src.tools.urls import run_get_public_url
        result = run_get_public_url("logos/mmiri28.png")
        assert result["ok"] is True
        assert "pub-test.r2.dev" in result["public_url"]

    def test_get_public_url_no_domain(self, r2):
        import src.tools.urls as urls_module
        original = urls_module.settings.public_domain
        urls_module.settings.public_domain = ""
        result = urls_module.run_get_public_url("any/key")
        assert result["ok"] is False
        urls_module.settings.public_domain = original

    def test_signed_url_invalid_operation(self, r2):
        from src.tools.urls import run_get_signed_url
        result = run_get_signed_url("any/key", operation="delete")
        assert result["ok"] is False
