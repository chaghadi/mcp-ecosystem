"""onboarding tables.

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
        CREATE TABLE IF NOT EXISTS onboarding_templates (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name        VARCHAR(255) NOT NULL,
            app_slug    VARCHAR(100) NOT NULL,
            role        VARCHAR(100) NOT NULL,
            description TEXT,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_onboarding_templates_app ON onboarding_templates (app_slug)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS onboarding_template_steps (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            template_id UUID NOT NULL REFERENCES onboarding_templates(id) ON DELETE CASCADE,
            step_order  INTEGER NOT NULL,
            title       VARCHAR(500) NOT NULL,
            description TEXT,
            day_offset  INTEGER NOT NULL DEFAULT 1,
            required    BOOLEAN NOT NULL DEFAULT true
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_steps_template ON onboarding_template_steps (template_id, step_order)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS onboardings (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            template_id  UUID NOT NULL REFERENCES onboarding_templates(id) ON DELETE CASCADE,
            user_id      VARCHAR(255) NOT NULL,
            user_name    VARCHAR(255) NOT NULL,
            app_slug     VARCHAR(100) NOT NULL,
            start_date   DATE NOT NULL,
            status       VARCHAR(20) NOT NULL DEFAULT 'active',
            started_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            completed_at TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_onboardings_status ON onboardings (status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_onboardings_app    ON onboardings (app_slug)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS onboarding_step_completions (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            onboarding_id   UUID NOT NULL REFERENCES onboardings(id) ON DELETE CASCADE,
            step_id         UUID NOT NULL REFERENCES onboarding_template_steps(id) ON DELETE CASCADE,
            notes           TEXT,
            completed_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (onboarding_id, step_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_step_completions_onboarding ON onboarding_step_completions (onboarding_id)")


def downgrade() -> None:
    pass
