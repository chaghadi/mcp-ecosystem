"""billing_customers and billing_subscriptions tables.

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
        CREATE TABLE IF NOT EXISTS billing_customers (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            provider        VARCHAR(20) NOT NULL,
            provider_id     VARCHAR(255) NOT NULL,
            email           VARCHAR(255),
            currency        VARCHAR(10) NOT NULL DEFAULT 'USD',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (user_id, provider)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_billing_customers_user ON billing_customers (user_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS billing_subscriptions (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            provider            VARCHAR(20) NOT NULL,
            subscription_id     VARCHAR(255) UNIQUE NOT NULL,
            plan_id             VARCHAR(255) NOT NULL,
            status              VARCHAR(50) NOT NULL DEFAULT 'active',
            currency            VARCHAR(10) NOT NULL,
            amount              INTEGER NOT NULL,
            interval            VARCHAR(20) NOT NULL,
            current_period_end  TIMESTAMPTZ,
            trial_end           TIMESTAMPTZ,
            cancel_at_period_end BOOLEAN NOT NULL DEFAULT false,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_billing_subs_user ON billing_subscriptions (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_billing_subs_status ON billing_subscriptions (status)")


def downgrade() -> None:
    pass
