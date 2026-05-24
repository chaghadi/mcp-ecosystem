"""experiments, assignments, conversions tables.

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
        CREATE TABLE IF NOT EXISTS experiments (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name            VARCHAR(255) UNIQUE NOT NULL,
            app_slug        VARCHAR(100) NOT NULL,
            variants        JSONB NOT NULL,
            goal_event      VARCHAR(255) NOT NULL,
            description     TEXT,
            status          VARCHAR(20) NOT NULL DEFAULT 'active',
            winning_variant VARCHAR(100),
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            ended_at        TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_experiments_app ON experiments (app_slug)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_experiments_status ON experiments (status)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS experiment_assignments (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            experiment_id   UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
            user_id         VARCHAR(255) NOT NULL,
            variant         VARCHAR(100) NOT NULL,
            assigned_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (experiment_id, user_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_assignments_exp ON experiment_assignments (experiment_id, variant)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS experiment_conversions (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            experiment_id   UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
            user_id         VARCHAR(255) NOT NULL,
            variant         VARCHAR(100) NOT NULL,
            value           DECIMAL(12, 2) NOT NULL DEFAULT 0,
            converted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_conversions_exp ON experiment_conversions (experiment_id, variant)")


def downgrade() -> None:
    pass
