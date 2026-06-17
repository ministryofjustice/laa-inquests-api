"""rename_provider_email_to_email_address

Revision ID: 630fc3479944
Revises: 7a4f5f615543
Create Date: 2026-06-17 16:56:00.636061

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "630fc3479944"
down_revision: Union[str, None] = "7a4f5f615543"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("provider", "email", new_column_name="email_address")


def downgrade() -> None:
    op.alter_column("provider", "email_address", new_column_name="email")
