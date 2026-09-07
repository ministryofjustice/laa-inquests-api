"""add POA_AUTO_APPROVE_EMAIL_SENT to historyeventreference enum

Revision ID: 072b60aa9b4e
Revises: idds_472_laa_reference
Create Date: 2026-09-07 14:26:04.923706

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "072b60aa9b4e"
down_revision: str | None = "idds_472_laa_reference"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE historyeventreference ADD VALUE IF NOT EXISTS "
        "'POA_AUTO_APPROVE_EMAIL_SENT'"
    )
