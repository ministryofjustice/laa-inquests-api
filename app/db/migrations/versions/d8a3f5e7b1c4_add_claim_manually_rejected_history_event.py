"""Add CLAIM_REJECTED_EMAIL to historyeventreference enum

Revision ID: d8a3f5e7b1c4
Revises: c4f1a2b3d5e6
Create Date: 2026-08-18 11:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d8a3f5e7b1c4"
down_revision: Union[str, None] = "c4f1a2b3d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE historyeventreference ADD VALUE 'CLAIM_REJECTED_EMAIL'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from an enum type directly.
    # A full recreation would be needed if a downgrade is required.
    pass

