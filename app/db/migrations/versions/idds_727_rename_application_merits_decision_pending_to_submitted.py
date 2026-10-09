"""Rename application merits decision PENDING to SUBMITTED.

Revision ID: idds_727_merits_decision_submitted
Revises: idds_597_cpe_created_at_idx
Create Date: 2026-10-09 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "idds_727_merits_decision_submitted"
down_revision: Union[str, None] = "idds_597_cpe_created_at_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE application_proceeding "
        "SET merits_decision = 'SUBMITTED' "
        "WHERE merits_decision = 'PENDING'"
    )
    op.alter_column(
        "application_proceeding",
        "merits_decision",
        existing_type=sa.VARCHAR(),
        server_default="SUBMITTED",
    )


def downgrade() -> None:
    op.execute(
        "UPDATE application_proceeding "
        "SET merits_decision = 'PENDING' "
        "WHERE merits_decision = 'SUBMITTED'"
    )
    op.alter_column(
        "application_proceeding",
        "merits_decision",
        existing_type=sa.VARCHAR(),
        server_default="PENDING",
    )
