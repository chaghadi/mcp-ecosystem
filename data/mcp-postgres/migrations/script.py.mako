"""${message}

Revision ID: ${up_revision}
Revises:     ${down_revision | comma,n}
Created:     ${create_date}

Per ADR-0005: downgrade() is intentionally left empty.
Rollbacks are handled by writing a new forward migration.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    # Write your schema changes here.
    # Keep this migration small — one concern per file (see ADR-0005).
    pass


def downgrade() -> None:
    # Intentionally empty — see ADR-0005.
    # To undo a migration, create a new forward migration that reverses the change.
    pass
