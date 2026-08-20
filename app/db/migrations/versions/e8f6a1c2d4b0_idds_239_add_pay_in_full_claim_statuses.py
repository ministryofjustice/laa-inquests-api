"""IDDS-239 add PAY_IN_FULL to claim enums

Revision ID: e8f6a1c2d4b0
Revises: c235530a87b5
Create Date: 2026-07-23 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e8f6a1c2d4b0"
down_revision: Union[str, None] = "c235530a87b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE claimstatus ADD VALUE IF NOT EXISTS 'PAY_IN_FULL'")
    op.execute("ALTER TYPE claimdecisionstatus ADD VALUE IF NOT EXISTS 'PAY_IN_FULL'")


def downgrade() -> None:
    # PostgreSQL does not support dropping enum values directly.
    pass
