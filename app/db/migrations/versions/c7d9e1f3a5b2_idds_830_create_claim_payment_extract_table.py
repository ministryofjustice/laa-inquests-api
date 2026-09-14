"""idds_830_create_claim_payment_extract_table

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


def upgrade() -> None:
    op.create_table(
        "claim_payment_extract",
        sa.Column("claim_payment_extract_id", sa.Integer(), nullable=False),
        sa.Column("claim_id", sa.Integer(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("invoice_number", sa.String(), nullable=False),
        sa.Column(
            "invoice_amount",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
        ),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column(
            "invoice_type",
            sa.Enum(
                "FINAL_BILL_FEES",
                "FINAL_BILL_DISBURSEMENT",
                "POA",
                "RECOUPED",
                name="invoicetypecode",
            ),
            nullable=False,
        ),
        sa.Column(
            "tax_code",
            sa.Enum("GB_VAT_20", "ZERO_VAT", name="taxcode"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["claim_id"], ["claim.claim_id"]),
        sa.PrimaryKeyConstraint("claim_payment_extract_id"),
        sa.UniqueConstraint("claim_id", "sequence_number"),
        sa.UniqueConstraint("invoice_number"),
    )


def downgrade() -> None:
    op.drop_table("claim_payment_extract")
    sa.Enum(name="invoicetypecode").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="taxcode").drop(op.get_bind(), checkfirst=True)
