"""email_lists, email_subscribers, email_campaigns.

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
        CREATE TABLE IF NOT EXISTS email_lists (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name        VARCHAR(255) NOT NULL,
            app_slug    VARCHAR(100) NOT NULL,
            description TEXT,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_email_lists_app ON email_lists (app_slug)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS email_subscribers (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            list_id           UUID NOT NULL REFERENCES email_lists(id) ON DELETE CASCADE,
            email             VARCHAR(255) NOT NULL,
            name              VARCHAR(255),
            metadata          JSONB NOT NULL DEFAULT '{}',
            unsubscribe_token VARCHAR(255) UNIQUE NOT NULL,
            is_active         BOOLEAN NOT NULL DEFAULT true,
            subscribed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            unsubscribed_at   TIMESTAMPTZ,
            UNIQUE (list_id, email)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_subscribers_list ON email_subscribers (list_id) WHERE is_active = true")
    op.execute("CREATE INDEX IF NOT EXISTS idx_subscribers_email ON email_subscribers (email)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS email_campaigns (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            list_id         UUID NOT NULL REFERENCES email_lists(id) ON DELETE CASCADE,
            subject         VARCHAR(500) NOT NULL,
            html_body       TEXT NOT NULL,
            status          VARCHAR(20) NOT NULL DEFAULT 'draft',
            recipient_count INTEGER NOT NULL DEFAULT 0,
            sent_count      INTEGER NOT NULL DEFAULT 0,
            failed_count    INTEGER NOT NULL DEFAULT 0,
            test_mode       BOOLEAN NOT NULL DEFAULT false,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            sent_at         TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_campaigns_list ON email_campaigns (list_id, created_at DESC)")


def downgrade() -> None:
    pass
