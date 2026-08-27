"""idds_706_add_final_bill_claim_fields

Revision ID: b2f4c6a8d0e1
Revises: 965237adae9c
Create Date: 2026-08-26 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2f4c6a8d0e1"
down_revision: Union[str, None] = "965237adae9c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


number_of_counsel_instructed_enum = sa.Enum(
    "0",
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "MORE_THAN_6",
    name="numberofcounselinstructed",
)


def upgrade() -> None:
    number_of_counsel_instructed_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "claim",
        sa.Column("has_counsel_been_paid", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "claim",
        sa.Column("has_alternative_funding", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "claim",
        sa.Column("has_recovery_costs_awarded", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "claim",
        sa.Column(
            "financial_recovery_previous_pre_certificate_costs",
            sa.Numeric(precision=10, scale=2),
            nullable=True,
        ),
    )
    op.add_column(
        "claim",
        sa.Column(
            "financial_recovery_cost",
            sa.Numeric(precision=10, scale=2),
            nullable=True,
        ),
    )
    op.add_column(
        "claim",
        sa.Column(
            "financial_recovery_damages",
            sa.Numeric(precision=10, scale=2),
            nullable=True,
        ),
    )
    op.add_column(
        "claim",
        sa.Column(
            "financial_recovery_interest",
            sa.Numeric(precision=10, scale=2),
            nullable=True,
        ),
    )
    op.add_column(
        "claim",
        sa.Column("paying_party", sa.String(), nullable=True),
    )
    op.add_column(
        "claim",
        sa.Column(
            "number_of_counsel_instructed",
            number_of_counsel_instructed_enum,
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("claim", "number_of_counsel_instructed")
    op.drop_column("claim", "paying_party")
    op.drop_column("claim", "financial_recovery_interest")
    op.drop_column("claim", "financial_recovery_damages")
    op.drop_column("claim", "financial_recovery_cost")
    op.drop_column("claim", "financial_recovery_previous_pre_certificate_costs")
    op.drop_column("claim", "has_recovery_costs_awarded")
    op.drop_column("claim", "has_alternative_funding")
    op.drop_column("claim", "has_counsel_been_paid")
    number_of_counsel_instructed_enum.drop(op.get_bind(), checkfirst=True)
