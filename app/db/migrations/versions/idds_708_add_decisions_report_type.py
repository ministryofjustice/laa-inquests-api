"""add DECISIONS to reporttype enum and merge heads

Revision ID: idds_708_decisions_report
Revises: idds_731_audit_trail_extract, 98afb9a716c2
Create Date: 2026-10-26 14:10:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "idds_708_decisions_report"
down_revision: str | Sequence[str] | None = (
    "idds_731_audit_trail_extract"
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE reporttype ADD VALUE IF NOT EXISTS 'DECISIONS'")


def downgrade() -> None:
    # PostgreSQL cannot remove a value from an enum type.
    pass
