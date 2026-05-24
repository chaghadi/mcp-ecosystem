"""search_index table.

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
        CREATE TABLE IF NOT EXISTS search_index (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            doc_id        VARCHAR(255) NOT NULL,
            app_slug      VARCHAR(100) NOT NULL,
            title         VARCHAR(500) NOT NULL DEFAULT '',
            content       TEXT NOT NULL,
            metadata      JSONB NOT NULL DEFAULT '{}',
            search_vector tsvector,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (app_slug, doc_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_search_vector ON search_index USING gin(search_vector)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_search_app    ON search_index (app_slug)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_search_meta   ON search_index USING gin(metadata)")


def downgrade() -> None:
    pass
