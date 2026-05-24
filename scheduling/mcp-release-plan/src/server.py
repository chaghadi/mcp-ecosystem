"""server.py — mcp-release-plan MCP server entry point.

Track releases, features, and ship dates across apps.
Integrates conceptually with mcp-changelog and mcp-git-ops.
"""

import subprocess
import uuid
from datetime import datetime, timezone
from typing import Any

import psycopg2

from mcp.server.fastmcp import FastMCP
from src.config import settings
from src.db import dict_cursor, get_conn

mcp = FastMCP(
    "mcp-release-plan",
    instructions="Release planning MCP for mmiri28 solutions. Track releases by version, ship dates, and features. Status workflow: planned → in_progress → released.",
)


@mcp.tool()
def health_check() -> dict:
    err = settings.validate()
    if err: return {"ok": False, "error": err}
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM releases")
                total = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM releases WHERE status = 'planned'")
                planned = cur.fetchone()[0]
        return {"ok": True, "total_releases": total, "planned": planned}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


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
def create_release(
    name: str, version: str, app_slug: str,
    scheduled_date: str | None = None, description: str = "",
) -> dict[str, Any]:
    """
    Create a new release plan.

    Args:
        name:           Release name (e.g. "Q3 2026 launch").
        version:        Semver string (e.g. "1.2.0").
        app_slug:       App this release belongs to.
        scheduled_date: ISO date when shipping is planned (optional).
        description:    Release theme or summary.
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                release_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO releases
                        (id, name, version, app_slug, scheduled_date,
                         description, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, 'planned', %s)
                """, [release_id, name, version, app_slug,
                      scheduled_date, description, datetime.now(timezone.utc)])
        return {"ok": True, "release_id": release_id, "name": name, "version": version}
    except psycopg2.IntegrityError:
        return {"ok": False, "error": f"Release '{version}' already exists for '{app_slug}'."}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def add_feature(
    release_id: str, title: str, description: str = "",
    owner: str = "", priority: str = "medium",
) -> dict[str, Any]:
    """
    Add a feature to a release.

    Args:
        release_id:  UUID of the release.
        title:       Feature name.
        description: Feature details.
        owner:       Person responsible (e.g. email or username).
        priority:    "low" | "medium" | "high" | "critical"
    """
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                feature_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO release_features
                        (id, release_id, title, description, owner,
                         priority, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, 'planned', %s)
                """, [feature_id, release_id, title, description,
                      owner, priority, datetime.now(timezone.utc)])
        return {"ok": True, "feature_id": feature_id, "title": title,
                "release_id": release_id}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def update_status(
    release_id: str, status: str,
) -> dict[str, Any]:
    """
    Update release status.

    Args:
        release_id: UUID.
        status:     "planned" | "in_progress" | "in_review" | "released" | "cancelled"
    """
    if status not in {"planned", "in_progress", "in_review", "released", "cancelled"}:
        return {"ok": False, "error": "Invalid status."}
    try:
        released_at = datetime.now(timezone.utc) if status == "released" else None
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    UPDATE releases SET status = %s, released_at = COALESCE(%s, released_at)
                    WHERE id = %s RETURNING id
                """, [status, released_at, release_id])
                if not cur.fetchone():
                    return {"ok": False, "error": "Release not found"}
        return {"ok": True, "release_id": release_id, "status": status}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def update_feature_status(feature_id: str, status: str) -> dict[str, Any]:
    """
    Update a feature's status.

    status: "planned" | "in_progress" | "in_review" | "done" | "cut"
    """
    if status not in {"planned", "in_progress", "in_review", "done", "cut"}:
        return {"ok": False, "error": "Invalid status."}
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("UPDATE release_features SET status = %s WHERE id = %s RETURNING id",
                            [status, feature_id])
                if not cur.fetchone():
                    return {"ok": False, "error": "Feature not found"}
        return {"ok": True, "feature_id": feature_id, "status": status}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def list_releases(
    app_slug: str | None = None, status: str | None = None,
) -> dict[str, Any]:
    """List releases with optional filters."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                conditions, params = [], []
                if app_slug:
                    conditions.append("app_slug = %s"); params.append(app_slug)
                if status:
                    conditions.append("status = %s"); params.append(status)
                where = "WHERE " + " AND ".join(conditions) if conditions else ""
                cur.execute(f"""
                    SELECT r.*,
                        (SELECT COUNT(*) FROM release_features WHERE release_id = r.id) AS total_features,
                        (SELECT COUNT(*) FROM release_features WHERE release_id = r.id AND status = 'done') AS done_features
                    FROM releases r {where} ORDER BY r.scheduled_date NULLS LAST, r.created_at DESC
                """, params)
                releases = [dict(row) for row in cur.fetchall()]
        return {"ok": True, "count": len(releases), "releases": releases}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def get_release(release_id: str) -> dict[str, Any]:
    """Get release details with all features."""
    try:
        with get_conn() as conn:
            with dict_cursor(conn) as cur:
                cur.execute("SELECT * FROM releases WHERE id = %s", [release_id])
                release = cur.fetchone()
                if not release:
                    return {"ok": False, "error": "Release not found"}
                cur.execute("""
                    SELECT * FROM release_features WHERE release_id = %s
                    ORDER BY CASE priority
                        WHEN 'critical' THEN 1 WHEN 'high' THEN 2
                        WHEN 'medium' THEN 3 WHEN 'low' THEN 4 END,
                    created_at
                """, [release_id])
                features = [dict(f) for f in cur.fetchall()]
        return {"ok": True, "release": dict(release), "features": features}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def generate_release_notes(release_id: str, format: str = "markdown") -> dict[str, Any]:
    """
    Auto-generate release notes from completed features.

    Args:
        release_id: UUID of the release.
        format:     "markdown" | "html" | "plaintext"
    """
    data = get_release(release_id)
    if not data["ok"]:
        return data

    release = data["release"]
    features = [f for f in data["features"] if f["status"] == "done"]
    cut = [f for f in data["features"] if f["status"] == "cut"]

    if format == "markdown":
        lines = [
            f"# {release['name']} — v{release['version']}",
            f"\n*{release.get('description', '')}*\n" if release.get("description") else "",
            "\n## ✨ What's new\n",
        ]
        for f in features:
            lines.append(f"- **{f['title']}** — {f['description']}")
        if cut:
            lines.append("\n## ⏭️ Cut from this release")
            for f in cut:
                lines.append(f"- {f['title']}")
        notes = "\n".join(lines)
    else:
        notes = f"{release['name']} v{release['version']}\n\n"
        notes += "\n".join(f"- {f['title']}: {f['description']}" for f in features)

    return {"ok": True, "release": release["name"], "version": release["version"],
            "feature_count": len(features), "notes": notes}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
