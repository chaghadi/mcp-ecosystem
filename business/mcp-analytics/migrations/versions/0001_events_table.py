"""events table for mcp-analytics.

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
        CREATE TABLE IF NOT EXISTS events (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id     UUID REFERENCES users(id) ON DELETE SET NULL,
            app_slug    VARCHAR(100) NOT NULL,
            event_name  VARCHAR(255) NOT NULL,
            properties  JSONB NOT NULL DEFAULT '{}',
            session_id  VARCHAR(255),
            ip_address  INET,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_events_user       ON events (user_id)    WHERE user_id IS NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS idx_events_app        ON events (app_slug)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_events_name       ON events (event_name)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_events_created    ON events (created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_events_gin        ON events USING gin (properties)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_events_app_name   ON events (app_slug, event_name, created_at DESC)")


def downgrade() -> None:
    pass
