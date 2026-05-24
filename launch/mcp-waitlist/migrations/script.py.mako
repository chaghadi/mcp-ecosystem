"""${message}

Revision ID: ${up_revision}
Revises:     ${down_revision | comma,n}
Created:     ${create_date}

Per ADR-0005: downgrade() is intentionally left empty.
"""

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    pass


def downgrade() -> None:
    # Intentionally empty — see ADR-0005
    pass
