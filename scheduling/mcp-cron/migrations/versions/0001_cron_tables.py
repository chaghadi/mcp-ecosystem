"""cron_jobs and cron_executions tables.

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
        CREATE TABLE IF NOT EXISTS cron_jobs (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name            VARCHAR(255) UNIQUE NOT NULL,
            cron_expression VARCHAR(100) NOT NULL,
            action_type     VARCHAR(50) NOT NULL,
            action_payload  JSONB NOT NULL DEFAULT '{}',
            app_slug        VARCHAR(100) NOT NULL DEFAULT 'system',
            description     TEXT,
            last_run        TIMESTAMPTZ,
            next_run        TIMESTAMPTZ NOT NULL,
            is_active       BOOLEAN NOT NULL DEFAULT true,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_cron_due ON cron_jobs (next_run) WHERE is_active = true")
    op.execute("CREATE INDEX IF NOT EXISTS idx_cron_app ON cron_jobs (app_slug)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS cron_executions (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            job_id        UUID NOT NULL REFERENCES cron_jobs(id) ON DELETE CASCADE,
            status        VARCHAR(20) NOT NULL,
            output        TEXT,
            error_message TEXT,
            executed_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_cron_exec_job ON cron_executions (job_id, executed_at DESC)")


def downgrade() -> None:
    pass
