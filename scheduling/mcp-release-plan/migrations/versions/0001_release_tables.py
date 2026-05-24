"""releases and release_features tables.

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
        CREATE TABLE IF NOT EXISTS releases (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name            VARCHAR(255) NOT NULL,
            version         VARCHAR(50) NOT NULL,
            app_slug        VARCHAR(100) NOT NULL,
            scheduled_date  DATE,
            released_at     TIMESTAMPTZ,
            description     TEXT,
            status          VARCHAR(30) NOT NULL DEFAULT 'planned',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (app_slug, version)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_releases_app    ON releases (app_slug)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_releases_status ON releases (status)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS release_features (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            release_id  UUID NOT NULL REFERENCES releases(id) ON DELETE CASCADE,
            title       VARCHAR(500) NOT NULL,
            description TEXT,
            owner       VARCHAR(255),
            priority    VARCHAR(20) NOT NULL DEFAULT 'medium',
            status      VARCHAR(30) NOT NULL DEFAULT 'planned',
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_features_release ON release_features (release_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_features_status  ON release_features (status)")


def downgrade() -> None:
    pass
