"""client.py — Cloudflare R2 client using boto3."""

import boto3
from botocore.config import Config
from src.config import settings


def get_client():
    """
    Return a boto3 S3 client pointed at Cloudflare R2.

    R2 is S3-compatible — boto3 works unchanged with a custom endpoint.
    Raises RuntimeError if credentials are not configured.
    """
    error = settings.validate()
    if error:
        raise RuntimeError(error)

    return boto3.client(
        "s3",
        endpoint_url=settings.endpoint_url,
        aws_access_key_id=settings.access_key_id,
        aws_secret_access_key=settings.secret_access_key,
        region_name="auto",
        config=Config(
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )


def check_connectivity() -> dict:
    """List buckets to verify credentials. Returns status dict — never raises."""
    error = settings.validate()
    if error:
        return {"ok": False, "error": error}
    try:
        client = get_client()
        response = client.list_buckets()
        buckets = [b["Name"] for b in response.get("Buckets", [])]
        return {"ok": True, "buckets": buckets}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
