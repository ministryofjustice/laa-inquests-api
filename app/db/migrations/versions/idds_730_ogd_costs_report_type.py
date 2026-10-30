"""IDDS-730 add OGD_COSTS to reporttype enum

Revision ID: idds_730_ogd_costs_report
Revises: idds_708_decisions_report
Create Date: 2026-10-29 17:30:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "idds_730_ogd_costs_report"
down_revision: str | Sequence[str] | None = "idds_708_decisions_report"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE reporttype ADD VALUE IF NOT EXISTS 'OGD_COSTS'")


def downgrade() -> None:
    # PostgreSQL cannot remove a value from an enum type.
    pass
