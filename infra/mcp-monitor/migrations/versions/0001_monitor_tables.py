"""monitored_endpoints and endpoint_checks tables.

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
        CREATE TABLE IF NOT EXISTS monitored_endpoints (
            id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            url                     TEXT NOT NULL,
            name                    VARCHAR(255) NOT NULL,
            app_slug                VARCHAR(100) NOT NULL,
            check_interval_minutes  INTEGER NOT NULL DEFAULT 5,
            expected_status         INTEGER NOT NULL DEFAULT 200,
            timeout_seconds         INTEGER NOT NULL DEFAULT 10,
            is_active               BOOLEAN NOT NULL DEFAULT true,
            created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_monitored_app ON monitored_endpoints (app_slug)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS endpoint_checks (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            endpoint_id   UUID NOT NULL REFERENCES monitored_endpoints(id) ON DELETE CASCADE,
            status        VARCHAR(20) NOT NULL,
            status_code   INTEGER,
            duration_ms   INTEGER,
            error_message TEXT,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_checks_endpoint ON endpoint_checks (endpoint_id, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_checks_status   ON endpoint_checks (status)")


def downgrade() -> None:
    pass
