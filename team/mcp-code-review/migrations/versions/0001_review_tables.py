"""review_requests and review_assignments tables.

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
        CREATE TABLE IF NOT EXISTS review_requests (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            repo          VARCHAR(255) NOT NULL,
            pr_number     INTEGER NOT NULL,
            pr_title      VARCHAR(500) NOT NULL,
            pr_url        TEXT NOT NULL,
            app_slug      VARCHAR(100) NOT NULL,
            requested_by  VARCHAR(255) NOT NULL,
            status        VARCHAR(20) NOT NULL DEFAULT 'open',
            requested_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            closed_at     TIMESTAMPTZ,
            UNIQUE (repo, pr_number)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_review_requests_status ON review_requests (status, requested_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_review_requests_app    ON review_requests (app_slug)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS review_assignments (
            id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            review_request_id  UUID NOT NULL REFERENCES review_requests(id) ON DELETE CASCADE,
            reviewer           VARCHAR(255) NOT NULL,
            status             VARCHAR(20) NOT NULL DEFAULT 'pending',
            decision           VARCHAR(30),
            comments           TEXT,
            assigned_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            completed_at       TIMESTAMPTZ,
            UNIQUE (review_request_id, reviewer)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_review_assignments_reviewer ON review_assignments (reviewer, status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_review_assignments_request  ON review_assignments (review_request_id)")


def downgrade() -> None:
    pass
