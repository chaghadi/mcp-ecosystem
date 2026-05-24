"""
server.py — mcp-storage MCP server entry point.

Tools:
  health_check()
  upload_file(key, file_path, bucket, content_type)
  upload_text(key, content, bucket, content_type)
  download_file(key, dest_path, bucket)
  download_text(key, bucket)
  delete_file(key, bucket)
  list_files(bucket, prefix, max_keys)
  file_exists(key, bucket)
  file_info(key, bucket)
  copy_file(source_key, dest_key, source_bucket, dest_bucket)
  get_signed_url(key, bucket, expires_in, operation)
  get_public_url(key)
"""

from mcp.server.fastmcp import FastMCP

from src.tools import files as _files
from src.tools import health as _health
from src.tools import urls as _urls

mcp = FastMCP(
    "mcp-storage",
    instructions=(
        "Cloudflare R2 storage MCP for mmiri28 solutions. "
        "Handles file upload, download, delete, listing, and URL generation. "
        "Supports private buckets (signed URLs) and public buckets (stable URLs)."
    ),
)


# ── Health ────────────────────────────────────────────────────────────────────

@mcp.tool()
def health_check() -> dict:
    """Verify R2 credentials by listing buckets."""
    return _health.run()


# ── Upload ────────────────────────────────────────────────────────────────────

@mcp.tool()
def upload_file(
    key: str,
    file_path: str,
    bucket: str | None = None,
    content_type: str = "application/octet-stream",
) -> dict:
    """
    Upload a local file to R2.

    Args:
        key:          Destination path in bucket (e.g. "avatars/user-1.jpg").
        file_path:    Local file path to upload.
        bucket:       Bucket name. Defaults to R2_DEFAULT_BUCKET.
        content_type: MIME type (e.g. "image/jpeg", "application/pdf").
    """
    return _files.run_upload_file(
        key=key, file_path=file_path, bucket=bucket, content_type=content_type
    )


@mcp.tool()
def upload_text(
    key: str,
    content: str,
    bucket: str | None = None,
    content_type: str = "text/plain",
) -> dict:
    """
    Upload a string directly to R2 — no local file needed.

    Args:
        key:          Destination key (e.g. "exports/report.json").
        content:      String content (text, JSON, HTML, CSV, etc.)
        bucket:       Bucket name. Defaults to R2_DEFAULT_BUCKET.
        content_type: MIME type. Default: "text/plain".
    """
    return _files.run_upload_text(
        key=key, content=content, bucket=bucket, content_type=content_type
    )


# ── Download ──────────────────────────────────────────────────────────────────

@mcp.tool()
def download_file(
    key: str,
    dest_path: str,
    bucket: str | None = None,
) -> dict:
    """
    Download a file from R2 to a local path.

    Args:
        key:       Source key in the bucket.
        dest_path: Local path to write the file to.
        bucket:    Bucket name. Defaults to R2_DEFAULT_BUCKET.
    """
    return _files.run_download_file(key=key, dest_path=dest_path, bucket=bucket)


@mcp.tool()
def download_text(key: str, bucket: str | None = None) -> dict:
    """
    Download a file from R2 and return its content as a string.

    Args:
        key:    Source key.
        bucket: Bucket name. Defaults to R2_DEFAULT_BUCKET.
    """
    return _files.run_download_text(key=key, bucket=bucket)


# ── Manage ────────────────────────────────────────────────────────────────────

@mcp.tool()
def delete_file(key: str, bucket: str | None = None) -> dict:
    """
    Delete a file from R2.

    Args:
        key:    Key to delete.
        bucket: Bucket name. Defaults to R2_DEFAULT_BUCKET.
    """
    return _files.run_delete_file(key=key, bucket=bucket)


@mcp.tool()
def list_files(
    bucket: str | None = None,
    prefix: str = "",
    max_keys: int = 100,
) -> dict:
    """
    List files in a bucket with optional prefix filter.

    Args:
        bucket:   Bucket name. Defaults to R2_DEFAULT_BUCKET.
        prefix:   Key prefix filter (e.g. "avatars/"). Default: all files.
        max_keys: Max results. Default: 100. Max: 1000.
    """
    return _files.run_list_files(bucket=bucket, prefix=prefix, max_keys=max_keys)


@mcp.tool()
def file_exists(key: str, bucket: str | None = None) -> dict:
    """
    Check whether a file exists in R2.

    Args:
        key:    Key to check.
        bucket: Bucket name. Defaults to R2_DEFAULT_BUCKET.
    """
    return _files.run_file_exists(key=key, bucket=bucket)


@mcp.tool()
def file_info(key: str, bucket: str | None = None) -> dict:
    """
    Get file metadata: size, content type, last modified, public URL.

    Args:
        key:    Key to inspect.
        bucket: Bucket name. Defaults to R2_DEFAULT_BUCKET.
    """
    return _files.run_file_info(key=key, bucket=bucket)


@mcp.tool()
def copy_file(
    source_key: str,
    dest_key: str,
    source_bucket: str | None = None,
    dest_bucket: str | None = None,
) -> dict:
    """
    Copy a file within R2 — same bucket or across buckets.

    Args:
        source_key:    Source key.
        dest_key:      Destination key.
        source_bucket: Source bucket. Defaults to R2_DEFAULT_BUCKET.
        dest_bucket:   Destination bucket. Defaults to same as source.
    """
    return _files.run_copy_file(
        source_key=source_key, dest_key=dest_key,
        source_bucket=source_bucket, dest_bucket=dest_bucket,
    )


# ── URLs ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_signed_url(
    key: str,
    bucket: str | None = None,
    expires_in: int = 3600,
    operation: str = "get",
) -> dict:
    """
    Generate a presigned URL for temporary access to a private file.

    Args:
        key:        File key.
        bucket:     Bucket name. Defaults to R2_DEFAULT_BUCKET.
        expires_in: Validity in seconds. Default: 3600 (1hr). Max: 604800 (7 days).
        operation:  "get" (download link) or "put" (direct upload link).
    """
    return _urls.run_get_signed_url(
        key=key, bucket=bucket, expires_in=expires_in, operation=operation
    )


@mcp.tool()
def get_public_url(key: str) -> dict:
    """
    Return the stable public URL for a file in a public bucket.
    Requires R2_PUBLIC_DOMAIN to be set in .env.

    Args:
        key: File key (e.g. "logos/mmiri28.png").
    """
    return _urls.run_get_public_url(key=key)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
