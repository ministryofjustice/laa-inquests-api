"""IDDS-709 add COST_LIMIT_FORECAST to reporttype enum

Revision ID: idds_709_forecast_report_type
Revises: idds_730_ogd_costs_report
Create Date: 2026-11-03 15:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "idds_709_forecast_report_type"
down_revision: str | Sequence[str] | None = "idds_730_ogd_costs_report"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE reporttype ADD VALUE IF NOT EXISTS 'COST_LIMIT_FORECAST'"
        )


def downgrade() -> None:
    # PostgreSQL cannot remove a value from an enum type.
    pass
