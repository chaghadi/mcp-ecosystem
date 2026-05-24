# mcp-storage

**Version:** 0.1.0 | **Runtime:** Python 3.12 | **Image:** `ghcr.io/chaghadi/mcp-storage`

Cloudflare R2 storage MCP for mmiri28 solutions. Private + public buckets, zero egress fees.

---

## Tools

| Tool | Description |
|------|-------------|
| `health_check()` | Verify credentials, list buckets |
| `upload_file(key, file_path, bucket, content_type)` | Upload from local path |
| `upload_text(key, content, bucket, content_type)` | Upload string directly |
| `download_file(key, dest_path, bucket)` | Download to local path |
| `download_text(key, bucket)` | Download as string |
| `delete_file(key, bucket)` | Delete a file |
| `list_files(bucket, prefix, max_keys)` | List files |
| `file_exists(key, bucket)` | Check existence |
| `file_info(key, bucket)` | Size, type, modified, public URL |
| `copy_file(source_key, dest_key, ...)` | Copy within or across buckets |
| `get_signed_url(key, bucket, expires_in, operation)` | Presigned URL (private) |
| `get_public_url(key)` | Stable URL (public bucket) |

---

## Setup

```powershell
cd data\mcp-storage
uv sync
copy .env.example .env
# Edit .env with your R2 credentials
uv run pytest tests/ -v
```

## Getting R2 credentials

1. **Cloudflare dashboard** → R2 → **Manage R2 API tokens**
2. Create a token with **Object Read & Write** permissions
3. Copy `Account ID`, `Access Key ID`, `Secret Access Key` into `.env`

## Bucket types

**Private bucket** — files accessible only via signed URLs:
```python
get_signed_url("invoices/inv-001.pdf", expires_in=3600)
# Returns a time-limited URL for the user to download
```

**Public bucket** — files accessible via stable URL:
```python
get_public_url("logos/mmiri28.png")
# Returns: https://pub-abc123.r2.dev/logos/mmiri28.png
```

For public buckets, enable public access in the Cloudflare R2 dashboard
and set `R2_PUBLIC_DOMAIN` in `.env`.
