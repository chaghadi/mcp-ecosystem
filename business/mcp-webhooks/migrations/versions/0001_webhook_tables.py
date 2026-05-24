"""webhook_endpoints and webhook_deliveries tables.

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
        CREATE TABLE IF NOT EXISTS webhook_endpoints (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            app_slug    VARCHAR(100) NOT NULL,
            url         TEXT NOT NULL,
            events      JSONB NOT NULL DEFAULT '[]',
            secret      VARCHAR(255) NOT NULL,
            description TEXT,
            is_active   BOOLEAN NOT NULL DEFAULT true,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_webhook_endpoints_app ON webhook_endpoints (app_slug)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_webhook_endpoints_events ON webhook_endpoints USING gin (events)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS webhook_deliveries (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            webhook_id    UUID NOT NULL REFERENCES webhook_endpoints(id) ON DELETE CASCADE,
            event_name    VARCHAR(255) NOT NULL,
            status        VARCHAR(20) NOT NULL DEFAULT 'pending',
            status_code   INTEGER,
            duration_ms   INTEGER,
            error_message TEXT,
            attempt       INTEGER NOT NULL DEFAULT 1,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_webhook ON webhook_deliveries (webhook_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_status  ON webhook_deliveries (status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_created ON webhook_deliveries (created_at DESC)")


def downgrade() -> None:
    pass
