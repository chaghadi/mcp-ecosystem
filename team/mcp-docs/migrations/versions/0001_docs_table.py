"""docs table.

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
        CREATE TABLE IF NOT EXISTS docs (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            title       VARCHAR(500) NOT NULL,
            slug        VARCHAR(100) NOT NULL,
            content     TEXT NOT NULL,
            app_slug    VARCHAR(100) NOT NULL,
            category    VARCHAR(100) NOT NULL DEFAULT 'general',
            tags        JSONB NOT NULL DEFAULT '[]',
            author      VARCHAR(255),
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (app_slug, slug)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_docs_app      ON docs (app_slug)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_docs_category ON docs (category)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_docs_tags     ON docs USING gin (tags)")


def downgrade() -> None:
    pass
