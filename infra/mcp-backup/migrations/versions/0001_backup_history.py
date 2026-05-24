"""backup_history table.

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
        CREATE TABLE IF NOT EXISTS backup_history (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            label            VARCHAR(255) NOT NULL,
            r2_key           TEXT NOT NULL,
            size_bytes       BIGINT,
            duration_seconds INTEGER,
            status           VARCHAR(20) NOT NULL,
            error_message    TEXT,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_backup_created ON backup_history (created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_backup_status  ON backup_history (status)")


def downgrade() -> None:
    pass
