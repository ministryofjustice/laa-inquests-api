"""IDDS-593 add CLAIM_FINAL_BILL_PAID_EMAIL to historyeventreference enum

Revision ID: b6b2a2fe79d7
Revises: 2392ff78c8f2
Create Date: 2026-09-15 11:35:43.828544

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b6b2a2fe79d7"
down_revision: str | None = "2392ff78c8f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE historyeventreference ADD VALUE IF NOT EXISTS "
        "'CLAIM_FINAL_BILL_PAID_EMAIL'"
    )


def downgrade() -> None:
    # PostgreSQL does not support removing values from an enum type directly.
    # A full recreation would be needed if a downgrade is required.
    pass
