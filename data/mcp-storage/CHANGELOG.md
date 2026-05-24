# mcp-storage Changelog

## [0.1.0] — 2026-05-24 — chaghadi

**Initial build. mmiri28 solutions.**

### Added
- `health_check` — verify R2 credentials, list buckets
- `upload_file` — upload from local path
- `upload_text` — upload string content directly
- `download_file` — download to local path
- `download_text` — download and return as string
- `delete_file` — delete a file
- `list_files` — list with optional prefix filter
- `file_exists` — check existence
- `file_info` — size, content type, last modified, public URL
- `copy_file` — copy within or across buckets
- `get_signed_url` — presigned URL for get or put (private files)
- `get_public_url` — stable public URL (public buckets)

### Architecture decisions recorded
- ADR-0007: Storage Strategy (Cloudflare R2, no egress fees)

### Notes
- Uses `boto3` only — no Cloudflare SDK, S3-compatible
- Tests use `moto` mock — no live R2 needed to run tests
- Docker image: `ghcr.io/chaghadi/mcp-storage`
