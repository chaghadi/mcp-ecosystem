"""
files.py — Core file operations for mcp-storage.

upload_file()    — upload from local path
upload_text()    — upload string/JSON content directly
download_file()  — download to local path
download_text()  — download and return content as string
delete_file()    — delete a file
list_files()     — list files with optional prefix filter
file_exists()    — check if a file exists
file_info()      — metadata: size, content type, last modified
copy_file()      — copy between keys or buckets
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from botocore.exceptions import ClientError

from src.client import get_client
from src.config import settings


def _bucket(bucket: str | None) -> str:
    return bucket or settings.default_bucket


def run_upload_file(
    key: str,
    file_path: str,
    bucket: str | None = None,
    content_type: str = "application/octet-stream",
) -> dict[str, Any]:
    """
    Upload a local file to R2.

    Args:
        key:          Destination key (path in the bucket), e.g. "avatars/user-1.jpg"
        file_path:    Absolute or relative path to the local file.
        bucket:       Bucket name. Defaults to R2_DEFAULT_BUCKET.
        content_type: MIME type. Defaults to "application/octet-stream".

    Returns:
        ok, bucket, key, size_bytes, public_url (if public domain is set).
    """
    path = Path(file_path)
    if not path.exists():
        return {"ok": False, "error": f"File not found: {file_path}"}
    try:
        client = get_client()
        b = _bucket(bucket)
        client.upload_file(
            str(path), b, key,
            ExtraArgs={"ContentType": content_type},
        )
        size = path.stat().st_size
        return {
            "ok": True,
            "bucket": b,
            "key": key,
            "size_bytes": size,
            "public_url": settings.public_url(key),
        }
    except ClientError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_upload_text(
    key: str,
    content: str,
    bucket: str | None = None,
    content_type: str = "text/plain",
) -> dict[str, Any]:
    """
    Upload a string directly to R2 without a local file.

    Args:
        key:          Destination key.
        content:      String content to upload (text, JSON, HTML, CSV, etc.)
        bucket:       Bucket name. Defaults to R2_DEFAULT_BUCKET.
        content_type: MIME type. Default: "text/plain".

    Returns:
        ok, bucket, key, size_bytes, public_url (if public domain is set).
    """
    try:
        client = get_client()
        b = _bucket(bucket)
        encoded = content.encode("utf-8")
        client.put_object(
            Bucket=b,
            Key=key,
            Body=encoded,
            ContentType=content_type,
        )
        return {
            "ok": True,
            "bucket": b,
            "key": key,
            "size_bytes": len(encoded),
            "public_url": settings.public_url(key),
        }
    except ClientError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_download_file(
    key: str,
    dest_path: str,
    bucket: str | None = None,
) -> dict[str, Any]:
    """
    Download a file from R2 to a local path.

    Args:
        key:       Source key in the bucket.
        dest_path: Local path to write the file to.
        bucket:    Bucket name. Defaults to R2_DEFAULT_BUCKET.
    """
    try:
        client = get_client()
        b = _bucket(bucket)
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        client.download_file(b, key, str(dest))
        return {
            "ok": True,
            "bucket": b,
            "key": key,
            "dest_path": str(dest),
            "size_bytes": dest.stat().st_size,
        }
    except ClientError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_download_text(
    key: str,
    bucket: str | None = None,
) -> dict[str, Any]:
    """
    Download a file from R2 and return its content as a string.

    Args:
        key:    Source key.
        bucket: Bucket name. Defaults to R2_DEFAULT_BUCKET.
    """
    try:
        client = get_client()
        b = _bucket(bucket)
        response = client.get_object(Bucket=b, Key=key)
        content = response["Body"].read().decode("utf-8")
        return {
            "ok": True,
            "bucket": b,
            "key": key,
            "content": content,
            "size_bytes": len(content.encode("utf-8")),
            "content_type": response.get("ContentType", "unknown"),
        }
    except ClientError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_delete_file(key: str, bucket: str | None = None) -> dict[str, Any]:
    """
    Delete a file from R2.

    Args:
        key:    Key to delete.
        bucket: Bucket name. Defaults to R2_DEFAULT_BUCKET.
    """
    try:
        client = get_client()
        b = _bucket(bucket)
        client.delete_object(Bucket=b, Key=key)
        return {"ok": True, "bucket": b, "key": key, "deleted": True}
    except ClientError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_list_files(
    bucket: str | None = None,
    prefix: str = "",
    max_keys: int = 100,
) -> dict[str, Any]:
    """
    List files in a bucket with an optional prefix filter.

    Args:
        bucket:   Bucket name. Defaults to R2_DEFAULT_BUCKET.
        prefix:   Key prefix to filter by (e.g. "avatars/").
        max_keys: Maximum number of results. Default: 100. Max: 1000.

    Returns:
        files list with key, size, last_modified, and public_url.
    """
    max_keys = min(max(1, max_keys), 1000)
    try:
        client = get_client()
        b = _bucket(bucket)
        response = client.list_objects_v2(
            Bucket=b,
            Prefix=prefix,
            MaxKeys=max_keys,
        )
        files = [
            {
                "key": obj["Key"],
                "size_bytes": obj["Size"],
                "last_modified": obj["LastModified"].isoformat(),
                "public_url": settings.public_url(obj["Key"]),
            }
            for obj in response.get("Contents", [])
        ]
        return {
            "ok": True,
            "bucket": b,
            "prefix": prefix,
            "file_count": len(files),
            "truncated": response.get("IsTruncated", False),
            "files": files,
        }
    except ClientError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_file_exists(key: str, bucket: str | None = None) -> dict[str, Any]:
    """
    Check whether a file exists in R2.

    Args:
        key:    Key to check.
        bucket: Bucket name. Defaults to R2_DEFAULT_BUCKET.
    """
    try:
        client = get_client()
        b = _bucket(bucket)
        client.head_object(Bucket=b, Key=key)
        return {"ok": True, "bucket": b, "key": key, "exists": True}
    except ClientError as exc:
        if exc.response["Error"]["Code"] in ("404", "NoSuchKey"):
            return {"ok": True, "bucket": b, "key": key, "exists": False}
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_file_info(key: str, bucket: str | None = None) -> dict[str, Any]:
    """
    Get metadata for a file: size, content type, last modified, public URL.

    Args:
        key:    Key to inspect.
        bucket: Bucket name. Defaults to R2_DEFAULT_BUCKET.
    """
    try:
        client = get_client()
        b = _bucket(bucket)
        response = client.head_object(Bucket=b, Key=key)
        return {
            "ok": True,
            "bucket": b,
            "key": key,
            "size_bytes": response["ContentLength"],
            "content_type": response.get("ContentType", "unknown"),
            "last_modified": response["LastModified"].isoformat(),
            "etag": response.get("ETag", "").strip('"'),
            "public_url": settings.public_url(key),
        }
    except ClientError as exc:
        if exc.response["Error"]["Code"] in ("404", "NoSuchKey"):
            return {"ok": False, "error": f"File '{key}' not found in bucket '{_bucket(bucket)}'."}
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_copy_file(
    source_key: str,
    dest_key: str,
    source_bucket: str | None = None,
    dest_bucket: str | None = None,
) -> dict[str, Any]:
    """
    Copy a file within R2 — same bucket or across buckets.

    Args:
        source_key:    Source key.
        dest_key:      Destination key.
        source_bucket: Source bucket. Defaults to R2_DEFAULT_BUCKET.
        dest_bucket:   Destination bucket. Defaults to same as source.
    """
    try:
        client = get_client()
        sb = _bucket(source_bucket)
        db = _bucket(dest_bucket) if dest_bucket else sb
        client.copy_object(
            CopySource={"Bucket": sb, "Key": source_key},
            Bucket=db,
            Key=dest_key,
        )
        return {
            "ok": True,
            "source": f"{sb}/{source_key}",
            "dest": f"{db}/{dest_key}",
            "public_url": settings.public_url(dest_key),
        }
    except ClientError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}
