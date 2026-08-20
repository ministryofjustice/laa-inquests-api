"""IDDS-505 add MANUAL_REJECTION reason code

Revision ID: c4f1a2b3d5e6
Revises: b7e4c9d1f2a3
Create Date: 2026-08-14 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c4f1a2b3d5e6"
down_revision: Union[str, None] = "b7e4c9d1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE reasoncode ADD VALUE IF NOT EXISTS 'MANUAL_REJECTION'")


def downgrade() -> None:
    # PostgreSQL does not support dropping enum values directly.
    pass
