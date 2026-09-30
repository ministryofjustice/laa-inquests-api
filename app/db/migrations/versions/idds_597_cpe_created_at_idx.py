"""IDDS-597 add index on claim_payment_extract.created_at

Revision ID: idds_597_cpe_created_at_idx
Revises: idds_867_backfill_hist_ref
Create Date: 2026-09-24 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "idds_597_cpe_created_at_idx"
down_revision: str | None = "idds_867_backfill_hist_ref"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        op.f("ix_claim_payment_extract_created_at"),
        "claim_payment_extract",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_claim_payment_extract_created_at"),
        table_name="claim_payment_extract",
    )
