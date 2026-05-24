"""press_releases, media_contacts, outreach_log tables.

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
        CREATE TABLE IF NOT EXISTS press_releases (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            title        VARCHAR(500) NOT NULL,
            content      TEXT NOT NULL,
            app_slug     VARCHAR(100) NOT NULL,
            embargo_date TIMESTAMPTZ,
            contact_info TEXT,
            status       VARCHAR(20) NOT NULL DEFAULT 'draft',
            created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_press_app    ON press_releases (app_slug)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_press_status ON press_releases (status)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS media_contacts (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name        VARCHAR(255) NOT NULL,
            email       VARCHAR(255) UNIQUE NOT NULL,
            outlet      VARCHAR(255) NOT NULL,
            beat        VARCHAR(100),
            twitter     VARCHAR(100),
            notes       TEXT,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_media_beat   ON media_contacts (beat)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_media_outlet ON media_contacts (outlet)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS outreach_log (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            contact_id        UUID NOT NULL REFERENCES media_contacts(id) ON DELETE CASCADE,
            press_release_id  UUID NOT NULL REFERENCES press_releases(id) ON DELETE CASCADE,
            status            VARCHAR(20) NOT NULL DEFAULT 'sent',
            notes             TEXT,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_outreach_contact ON outreach_log (contact_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_outreach_press   ON outreach_log (press_release_id)")


def downgrade() -> None:
    pass
