"""Initial auth schema — users, apps, roles, tokens.

Revision ID: 0001
Revises:
Created: 2026-05-24
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users ─────────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email           VARCHAR(255) UNIQUE,
            phone           VARCHAR(50) UNIQUE,
            username        VARCHAR(100) UNIQUE,
            password_hash   VARCHAR(255) NOT NULL,
            global_role     VARCHAR(50) NOT NULL DEFAULT 'user',
            is_active       BOOLEAN NOT NULL DEFAULT true,
            is_verified     BOOLEAN NOT NULL DEFAULT false,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT users_has_identifier CHECK (
                email IS NOT NULL OR phone IS NOT NULL OR username IS NOT NULL
            )
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_email    ON users (email)    WHERE email    IS NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_phone    ON users (phone)    WHERE phone    IS NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users (username) WHERE username IS NOT NULL")

    # ── apps ──────────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS apps (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            slug        VARCHAR(100) UNIQUE NOT NULL,
            name        VARCHAR(255) NOT NULL,
            is_active   BOOLEAN NOT NULL DEFAULT true,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # ── app_roles ─────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS app_roles (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            app_id      UUID NOT NULL REFERENCES apps(id) ON DELETE CASCADE,
            name        VARCHAR(100) NOT NULL,
            description TEXT,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (app_id, name)
        )
    """)

    # ── user_app_roles ────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_app_roles (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            app_id      UUID NOT NULL REFERENCES apps(id) ON DELETE CASCADE,
            role_id     UUID NOT NULL REFERENCES app_roles(id) ON DELETE CASCADE,
            assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            assigned_by UUID REFERENCES users(id),
            UNIQUE (user_id, app_id, role_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_app_roles_user ON user_app_roles (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_app_roles_app  ON user_app_roles (app_id)")

    # ── oauth_accounts ────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS oauth_accounts (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            provider         VARCHAR(50) NOT NULL,
            provider_user_id VARCHAR(255) NOT NULL,
            access_token     TEXT,
            refresh_token    TEXT,
            expires_at       TIMESTAMPTZ,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (provider, provider_user_id)
        )
    """)

    # ── refresh_tokens ────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash  VARCHAR(255) UNIQUE NOT NULL,
            app_slug    VARCHAR(100),
            expires_at  TIMESTAMPTZ NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            revoked_at  TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user   ON refresh_tokens (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash   ON refresh_tokens (token_hash)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expiry ON refresh_tokens (expires_at) WHERE revoked_at IS NULL")


def downgrade() -> None:
    # Intentionally empty — see ADR-0005
    pass
