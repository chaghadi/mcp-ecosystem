"""
urls.py — URL generation tools for mcp-storage.

get_signed_url()  — time-limited presigned URL for private files
get_public_url()  — stable public URL for public bucket files
"""

from typing import Any

from botocore.exceptions import ClientError

from src.client import get_client
from src.config import settings


def _bucket(bucket: str | None) -> str:
    return bucket or settings.default_bucket


def run_get_signed_url(
    key: str,
    bucket: str | None = None,
    expires_in: int = 3600,
    operation: str = "get",
) -> dict[str, Any]:
    """
    Generate a presigned URL for temporary access to a private file.

    Args:
        key:        File key in the bucket.
        bucket:     Bucket name. Defaults to R2_DEFAULT_BUCKET.
        expires_in: URL validity in seconds. Default: 3600 (1 hour). Max: 604800 (7 days).
        operation:  "get" (download) or "put" (upload). Default: "get".

    Returns:
        ok, signed_url, expires_in, operation.

    Use cases:
        - "get"  → share a private file temporarily (e.g. invoice download link)
        - "put"  → let a client upload directly to R2 without exposing credentials
    """
    if operation not in ("get", "put"):
        return {"ok": False, "error": "operation must be 'get' or 'put'."}

    expires_in = min(max(1, expires_in), 604800)

    client_method = "get_object" if operation == "get" else "put_object"

    try:
        client = get_client()
        b = _bucket(bucket)
        url = client.generate_presigned_url(
            client_method,
            Params={"Bucket": b, "Key": key},
            ExpiresIn=expires_in,
        )
        return {
            "ok": True,
            "bucket": b,
            "key": key,
            "signed_url": url,
            "expires_in_seconds": expires_in,
            "operation": operation,
            "note": (
                f"URL valid for {expires_in // 60} minute(s). "
                "Do not share put URLs publicly."
                if operation == "put"
                else f"URL valid for {expires_in // 60} minute(s)."
            ),
        }
    except ClientError as exc:
        return {"ok": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}


def run_get_public_url(key: str) -> dict[str, Any]:
    """
    Return the stable public URL for a file in a public bucket.

    Requires R2_PUBLIC_DOMAIN to be set in .env.
    The file must be in a bucket with public access enabled in Cloudflare R2.

    Args:
        key: File key (e.g. "logos/mmiri28.png").

    Returns:
        ok, public_url.
    """
    if not settings.public_domain:
        return {
            "ok": False,
            "error": (
                "R2_PUBLIC_DOMAIN is not set. "
                "Add your R2.dev subdomain or custom domain to .env: "
                "R2_PUBLIC_DOMAIN=https://pub-abc123.r2.dev"
            ),
        }
    url = settings.public_url(key)
    return {
        "ok": True,
        "key": key,
        "public_url": url,
        "note": "File must be in a bucket with public access enabled in Cloudflare R2 settings.",
    }
