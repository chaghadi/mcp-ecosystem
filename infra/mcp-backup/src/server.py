"""server.py — mcp-backup MCP server entry point.

Database backups via pg_dump uploaded to Cloudflare R2.
Restoration from R2 backups.
Backup history tracked in Postgres.
"""

import os
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
from botocore.client import Config
from mcp.server.fastmcp import FastMCP

from src.config import settings
from src.db import dict_cursor, get_conn

mcp = FastMCP(
    "mcp-backup",
    instructions="Database backup MCP for mmiri28 solutions. Postgres pg_dump uploaded to Cloudflare R2. Backup, restore, list, schedule.",
)


def _r2_client():
    if not settings.r2_access_key:
        raise RuntimeError("R2 credentials not configured.")
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key,
        aws_secret_access_key=settings.r2_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


@mcp.tool()
def health_check() -> dict:
    """Verify Postgres and R2 connectivity."""
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    results = {}
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version()")
                results["postgres"] = "connected"
    except Exception as exc:
        results["postgres"] = f"error: {exc}"

    try:
        client = _r2_client()
        client.head_bucket(Bucket=settings.r2_backup_bucket)
        results["r2"] = "connected"
    except Exception as exc:
        results["r2"] = f"error: {exc}"

    # Check pg_dump availability
    try:
        r = subprocess.run(["pg_dump", "--version"], capture_output=True, text=True, timeout=5)
        results["pg_dump"] = r.stdout.strip() if r.returncode == 0 else "not installed"
    except FileNotFoundError:
        results["pg_dump"] = "not installed — install PostgreSQL client tools"

    return {"ok": all("error" not in str(v) and "not installed" not in str(v) for v in results.values()),
            "checks": results, "backup_bucket": settings.r2_backup_bucket}


@mcp.tool()
def run_migrations() -> dict:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        capture_output=True, text=True, cwd=str(settings.mcp_root),
    )
    if result.returncode != 0:
        return {"ok": False, "error": result.stderr or result.stdout}
    return {"ok": True, "output": result.stdout or "Migrations applied."}


@mcp.tool()
def backup_database(
    database_url: str | None = None,
    label: str = "manual",
) -> dict[str, Any]:
    """
    Dump a Postgres database and upload to R2.

    Args:
        database_url: DB to back up. Default: configured DATABASE_URL.
        label:        Backup label (e.g. "manual", "pre-migration", "weekly").
    """
    err = settings.validate()
    if err: return {"ok": False, "error": err}

    db_url = database_url or settings.database_url
    backup_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = f"backup-{timestamp}-{label}-{backup_id[:8]}.sql"
    r2_key = f"postgres/{timestamp[:8]}/{filename}"

    # Run pg_dump
    with tempfile.NamedTemporaryFile(suffix=".sql", delete=False) as tmp:
        tmp_path = tmp.name

    start = datetime.now(timezone.utc)
    try:
        result = subprocess.run(
            ["pg_dump", db_url, "-f", tmp_path, "--no-owner", "--no-acl"],
            capture_output=True, text=True, timeout=600,
        )
        if result.returncode != 0:
            return {"ok": False, "error": result.stderr or "pg_dump failed"}

        size_bytes = os.path.getsize(tmp_path)

        # Upload to R2
        client = _r2_client()
        with open(tmp_path, "rb") as f:
            client.upload_fileobj(f, settings.r2_backup_bucket, r2_key,
                                   ExtraArgs={"ContentType": "application/sql"})

        duration_s = (datetime.now(timezone.utc) - start).total_seconds()

        # Log in DB
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    INSERT INTO backup_history
                        (id, label, r2_key, size_bytes, duration_seconds,
                         status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, [backup_id, label, r2_key, size_bytes,
                      int(duration_s), "success", datetime.now(timezone.utc)])

        return {
            "ok": True, "backup_id": backup_id, "r2_key": r2_key,
            "size_mb": round(size_bytes / 1024 / 1024, 2),
            "duration_seconds": round(duration_s, 1),
            "label": label,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "pg_dump timed out after 10 minutes"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@mcp.tool()
def list_backups(limit: int = 20) -> dict[str, Any]:
    """List recent database backups."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    SELECT id, label, r2_key, size_bytes, duration_seconds,
                           status, created_at
                    FROM backup_history ORDER BY created_at DESC LIMIT %s
                """, [min(limit, 100)])
                backups = []
                for r in cur.fetchall():
                    d = dict(r)
                    d["size_mb"] = round(d["size_bytes"] / 1024 / 1024, 2) if d["size_bytes"] else 0
                    backups.append(d)
        return {"ok": True, "count": len(backups), "backups": backups}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def restore_database(
    backup_id: str,
    target_database_url: str,
    confirm: bool = False,
) -> dict[str, Any]:
    """
    Restore a database from a backup.

    WARNING: this is destructive — it overwrites the target database.
    Set confirm=True to proceed.

    Args:
        backup_id:           Backup ID from list_backups.
        target_database_url: DB to restore into.
        confirm:             Must be True to actually restore.
    """
    if not confirm:
        return {"ok": False, "error": "Set confirm=True to proceed. This will overwrite the target database."}

    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("SELECT r2_key FROM backup_history WHERE id = %s", [backup_id])
                row = cur.fetchone()
        if not row:
            return {"ok": False, "error": f"Backup '{backup_id}' not found"}

        r2_key = row["r2_key"]
        with tempfile.NamedTemporaryFile(suffix=".sql", delete=False) as tmp:
            tmp_path = tmp.name

        # Download from R2
        client = _r2_client()
        with open(tmp_path, "wb") as f:
            client.download_fileobj(settings.r2_backup_bucket, r2_key, f)

        # Restore
        result = subprocess.run(
            ["psql", target_database_url, "-f", tmp_path],
            capture_output=True, text=True, timeout=600,
        )

        os.unlink(tmp_path)
        if result.returncode != 0:
            return {"ok": False, "error": result.stderr[-500:]}
        return {"ok": True, "backup_id": backup_id, "restored_to": "target database",
                "note": "Restoration complete. Verify your data."}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def delete_backup(backup_id: str, confirm: bool = False) -> dict[str, Any]:
    """Delete a backup from R2 and the history."""
    if not confirm:
        return {"ok": False, "error": "Set confirm=True to proceed."}
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("SELECT r2_key FROM backup_history WHERE id = %s", [backup_id])
                row = cur.fetchone()
                if not row:
                    return {"ok": False, "error": f"Backup '{backup_id}' not found"}

                client = _r2_client()
                client.delete_object(Bucket=settings.r2_backup_bucket, Key=row["r2_key"])

                cur.execute("DELETE FROM backup_history WHERE id = %s", [backup_id])

        return {"ok": True, "backup_id": backup_id, "deleted": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
