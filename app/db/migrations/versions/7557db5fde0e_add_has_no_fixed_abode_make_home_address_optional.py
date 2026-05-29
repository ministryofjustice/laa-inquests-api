"""Add has_no_fixed_abode and make home_address_id nullable on client

Revision ID: 7557db5fde0e
Revises: 48b9cef7f8a2
Create Date: 2026-05-26

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7557db5fde0e"
down_revision = "48b9cef7f8a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "client",
        sa.Column(
            "has_no_fixed_abode", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.alter_column(
        "client", "home_address_id", existing_type=sa.Integer(), nullable=True
    )


def downgrade() -> None:
    op.alter_column(
        "client", "home_address_id", existing_type=sa.Integer(), nullable=False
    )
    op.drop_column("client", "has_no_fixed_abode")
