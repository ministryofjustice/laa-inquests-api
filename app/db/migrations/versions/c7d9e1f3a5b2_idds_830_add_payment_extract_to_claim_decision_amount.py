"""idds_830_add_payment_extract_to_claim_decision_amount

Revision ID: c7d9e1f3a5b2
Revises: 2392ff78c8f2
Create Date: 2026-09-14 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c7d9e1f3a5b2"
down_revision: Union[str, None] = "2392ff78c8f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


invoice_type_code_enum = sa.Enum(
    "FINAL_BILL_FEES",
    "FINAL_BILL_DISBURSEMENT",
    "POA",
    "RECOUPED",
    name="invoicetypecode",
)

tax_code_enum = sa.Enum(
    "GB_VAT_20",
    "ZERO_VAT",
    name="taxcode",
)


def upgrade() -> None:
    invoice_type_code_enum.create(op.get_bind(), checkfirst=True)
    tax_code_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "claim_decision_amount",
        sa.Column("invoice_number", sa.String(), nullable=True),
    )
    op.add_column(
        "claim_decision_amount",
        sa.Column(
            "invoice_amount",
            sa.Numeric(precision=10, scale=2),
            nullable=True,
        ),
    )
    op.add_column(
        "claim_decision_amount",
        sa.Column("invoice_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "claim_decision_amount",
        sa.Column("invoice_type", invoice_type_code_enum, nullable=True),
    )
    op.add_column(
        "claim_decision_amount",
        sa.Column("tax_code", tax_code_enum, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("claim_decision_amount", "tax_code")
    op.drop_column("claim_decision_amount", "invoice_type")
    op.drop_column("claim_decision_amount", "invoice_date")
    op.drop_column("claim_decision_amount", "invoice_amount")
    op.drop_column("claim_decision_amount", "invoice_number")
    tax_code_enum.drop(op.get_bind(), checkfirst=True)
    invoice_type_code_enum.drop(op.get_bind(), checkfirst=True)
