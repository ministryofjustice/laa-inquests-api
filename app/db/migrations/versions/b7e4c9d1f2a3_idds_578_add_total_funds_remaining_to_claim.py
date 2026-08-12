"""IDDS-578 add total_funds_remaining_after_claim to claim

Revision ID: b7e4c9d1f2a3
Revises: 0588fd6aba84
Create Date: 2026-08-12 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7e4c9d1f2a3"
down_revision: Union[str, None] = "0588fd6aba84"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "claim",
        sa.Column(
            "total_funds_remaining_after_claim",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default="10000",
        ),
    )


def downgrade() -> None:
    op.drop_column("claim", "total_funds_remaining_after_claim")
