"""waitlists and waitlist_entries tables.

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
        CREATE TABLE IF NOT EXISTS waitlists (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name        VARCHAR(255) NOT NULL,
            app_slug    VARCHAR(100) NOT NULL,
            description TEXT,
            is_open     BOOLEAN NOT NULL DEFAULT true,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_waitlists_app ON waitlists (app_slug)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS waitlist_entries (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            waitlist_id      UUID NOT NULL REFERENCES waitlists(id) ON DELETE CASCADE,
            email            VARCHAR(255) NOT NULL,
            name             VARCHAR(255),
            position         INTEGER NOT NULL,
            referral_code    VARCHAR(20) UNIQUE NOT NULL,
            referred_by_id   UUID REFERENCES waitlist_entries(id) ON DELETE SET NULL,
            metadata         JSONB NOT NULL DEFAULT '{}',
            status           VARCHAR(20) NOT NULL DEFAULT 'waiting',
            joined_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            invited_at       TIMESTAMPTZ,
            UNIQUE (waitlist_id, email)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_waitlist_entries_position ON waitlist_entries (waitlist_id, position) WHERE status = 'waiting'")
    op.execute("CREATE INDEX IF NOT EXISTS idx_waitlist_entries_code ON waitlist_entries (referral_code)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_waitlist_entries_referrer ON waitlist_entries (referred_by_id)")


def downgrade() -> None:
    pass
