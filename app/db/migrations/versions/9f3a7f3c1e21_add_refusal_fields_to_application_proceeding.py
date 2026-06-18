"""add_refusal_fields_to_application_proceeding

Revision ID: 9f3a7f3c1e21
Revises: 630fc3479944
Create Date: 2026-06-18 12:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f3a7f3c1e21"
down_revision: Union[str, None] = "630fc3479944"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "application_proceeding",
        sa.Column("reason_for_refusal", sa.String(), nullable=True),
    )
    op.add_column(
        "application_proceeding",
        sa.Column("justification", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("application_proceeding", "justification")
    op.drop_column("application_proceeding", "reason_for_refusal")
