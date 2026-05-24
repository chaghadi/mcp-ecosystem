"""
migrate.py — Alembic migration tools.

migrate_up()         — run all pending migrations (alembic upgrade head).
migrate_status()     — show current revision and pending migrations.
create_migration()   — create a new migration file.

All commands run via subprocess so Alembic's own logging and error handling
are preserved exactly. CWD is set to the mcp-postgres root where alembic.ini lives.
"""

import subprocess
from typing import Any

from src.config import settings


def _run_alembic(*args: str) -> dict[str, Any]:
    """Run an alembic command via uv, return stdout/stderr/returncode."""
    result = subprocess.run(
        ["uv", "run", "alembic", *args],
        capture_output=True,
        text=True,
        cwd=str(settings.mcp_root),
    )
    return {
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def run_migrate_up(target: str = "head") -> dict[str, Any]:
    """
    Run pending Alembic migrations up to a target revision.

    Args:
        target: Alembic revision target. Default "head" runs all pending.
                Pass a specific revision ID to upgrade to that version only.

    Returns:
        ok:       True if migrations ran successfully.
        output:   Alembic log output.
        target:   The revision target used.
    """
    error = settings.validate()
    if error:
        return {"ok": False, "error": error}

    result = _run_alembic("upgrade", target)

    if result["returncode"] != 0:
        return {
            "ok": False,
            "error": result["stderr"] or result["stdout"],
            "target": target,
        }

    output = result["stdout"] or "No pending migrations. Already at target."
    return {
        "ok": True,
        "target": target,
        "output": output,
        "message": f"Migrations applied up to '{target}'.",
    }


def run_migrate_status() -> dict[str, Any]:
    """
    Show current Alembic revision and any pending migrations.

    Returns:
        current_revision: The applied revision ID (or 'None' if no migrations run).
        pending:          List of pending migration descriptions.
        output:           Full alembic history output.
    """
    error = settings.validate()
    if error:
        return {"ok": False, "error": error}

    # Current revision
    current = _run_alembic("current")
    # All pending (not yet applied)
    history = _run_alembic("history", "--indicate-current")

    if current["returncode"] != 0:
        return {"ok": False, "error": current["stderr"] or current["stdout"]}

    current_revision = current["stdout"] or "None (no migrations applied yet)"

    return {
        "ok": True,
        "current_revision": current_revision,
        "history": history["stdout"],
        "message": (
            "Run migrate_up() to apply pending migrations."
            if "head" not in current_revision
            else "Database is at head — no pending migrations."
        ),
    }


def run_create_migration(name: str) -> dict[str, Any]:
    """
    Create a new Alembic migration file.

    The migration file is created in migrations/versions/ with an auto-generated
    revision ID prefix. Edit the file to add your upgrade() SQL.

    Args:
        name: Short description of the migration.
              Use a verb phrase: "add_users_table", "add_email_index_to_users".
              Spaces are replaced with underscores automatically.

    Returns:
        ok:        True if the file was created.
        file_path: Path to the new migration file.
    """
    if not name or not name.strip():
        return {"error": "name cannot be empty. Example: 'add_users_table'"}

    safe_name = name.strip().lower().replace(" ", "_")
    result = _run_alembic("revision", "--autogenerate", "-m", safe_name)

    if result["returncode"] != 0:
        return {
            "ok": False,
            "error": result["stderr"] or result["stdout"],
            "note": (
                "Autogenerate requires SQLAlchemy models to be importable. "
                "If you have no models yet, use create_migration without --autogenerate: "
                "edit migrate.py to remove '--autogenerate' for blank migrations."
            ),
        }

    # Extract file path from alembic output (e.g. "Generating .../versions/abc123_name.py")
    file_path = None
    for line in result["stdout"].splitlines():
        if "Generating" in line or "versions/" in line:
            parts = line.split()
            for part in parts:
                if "versions/" in part:
                    file_path = part.rstrip(".")
                    break

    return {
        "ok": True,
        "migration_name": safe_name,
        "file_path": file_path or "Check migrations/versions/ for the new file.",
        "output": result["stdout"],
        "next_steps": [
            "1. Open the generated migration file in migrations/versions/",
            "2. Add your SQL to the upgrade() function",
            "3. Leave downgrade() empty (see ADR-0005)",
            "4. Run migrate_up() to apply it",
        ],
    }
