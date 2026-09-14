"""IDDS-609 add created_at to claim_decision

Revision ID: 2392ff78c8f2
Revises: 2157b7f59c80
Create Date: 2026-09-11 10:59:30.035840

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2392ff78c8f2"
down_revision: str | None = "2157b7f59c80"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "claim_decision", sa.Column("created_at", sa.DateTime(), nullable=True)
    )
    op.create_index(
        op.f("ix_claim_decision_created_at"),
        "claim_decision",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_claim_decision_created_at"), table_name="claim_decision")
    op.drop_column("claim_decision", "created_at")
