"""idds_706_rename_inquest_outcome_enum

Revision ID: 696fce63e2b7
Revises: b6b2a2fe79d7
Create Date: 2026-09-21 14:00:17.995018

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "696fce63e2b7"
down_revision: str | None = "b6b2a2fe79d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Align the DB enum type name with the model's derived name (inquestoutcomecode).
    op.execute("ALTER TYPE inquestoutcomeid RENAME TO inquestoutcomecode")


def downgrade() -> None:
    op.execute("ALTER TYPE inquestoutcomecode RENAME TO inquestoutcomeid")
