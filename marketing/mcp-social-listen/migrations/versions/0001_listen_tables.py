"""tracked_keywords and mentions tables.

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
        CREATE TABLE IF NOT EXISTS tracked_keywords (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            keyword     VARCHAR(255) NOT NULL,
            app_slug    VARCHAR(100) NOT NULL,
            platforms   JSONB NOT NULL DEFAULT '["twitter"]',
            is_active   BOOLEAN NOT NULL DEFAULT true,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_tracked_app ON tracked_keywords (app_slug)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS mentions (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            platform     VARCHAR(50) NOT NULL,
            platform_id  VARCHAR(255) NOT NULL,
            keyword      VARCHAR(255) NOT NULL,
            content      TEXT NOT NULL,
            author_id    VARCHAR(255),
            metrics      JSONB NOT NULL DEFAULT '{}',
            language     VARCHAR(10),
            created_at   TIMESTAMPTZ,
            fetched_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (platform, platform_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_mentions_keyword ON mentions (keyword, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mentions_platform ON mentions (platform)")


def downgrade() -> None:
    pass
