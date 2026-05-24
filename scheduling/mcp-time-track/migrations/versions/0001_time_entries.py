"""time_entries table.

Revision ID: 0001
Revises:
Created: 2026-05-24
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS time_entries (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id          VARCHAR(255) NOT NULL,
            app_slug         VARCHAR(100) NOT NULL,
            task             VARCHAR(500) NOT NULL,
            category         VARCHAR(100) NOT NULL DEFAULT '',
            notes            TEXT,
            started_at       TIMESTAMPTZ NOT NULL,
            ended_at         TIMESTAMPTZ,
            duration_seconds INTEGER
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_time_user_started ON time_entries (user_id, started_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_time_app          ON time_entries (app_slug)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_time_running      ON time_entries (user_id) WHERE ended_at IS NULL")


def downgrade() -> None:
    pass
