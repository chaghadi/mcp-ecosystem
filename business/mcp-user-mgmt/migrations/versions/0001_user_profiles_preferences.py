"""user_profiles and user_preferences tables.

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
    # ── user_profiles ─────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id      UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            display_name VARCHAR(100),
            bio          TEXT,
            avatar_url   TEXT,
            location     VARCHAR(100),
            website      VARCHAR(255),
            timezone     VARCHAR(100),
            created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_profiles_user ON user_profiles (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_profiles_name ON user_profiles (display_name) WHERE display_name IS NOT NULL")

    # ── user_preferences ──────────────────────────────────────────────────────
    # Flexible JSONB — namespaced by app slug
    # { "global": { "timezone": "Europe/Vienna" }, "marketplace": { "theme": "dark" } }
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id     UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            preferences JSONB NOT NULL DEFAULT '{}',
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_preferences_user ON user_preferences (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_preferences_gin  ON user_preferences USING gin (preferences)")


def downgrade() -> None:
    # Intentionally empty — see ADR-0005
    pass
