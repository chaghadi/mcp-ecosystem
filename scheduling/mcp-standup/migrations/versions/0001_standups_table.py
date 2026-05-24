"""standups table.

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
        CREATE TABLE IF NOT EXISTS standups (
            id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id    VARCHAR(255) NOT NULL,
            app_slug   VARCHAR(100) NOT NULL,
            date       DATE NOT NULL,
            yesterday  TEXT NOT NULL,
            today      TEXT NOT NULL,
            blockers   TEXT,
            mood       VARCHAR(50),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (user_id, app_slug, date)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_standups_team_date ON standups (app_slug, date DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_standups_user      ON standups (user_id, date DESC)")


def downgrade() -> None:
    pass
