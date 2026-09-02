"""IDDS-472 rename laa_reference to application_id

Revision ID: 85739150dcc5
Revises: d2aca39c7115
Create Date: 2026-09-02 15:41:35.100925

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '85739150dcc5'
down_revision: Union[str, None] = 'd2aca39c7115'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("application", "laa_reference", new_column_name="application_id")
    op.alter_column(
        "application_proceeding", "laa_reference", new_column_name="application_id"
    )
    op.alter_column(
        "application_public_body", "laa_reference", new_column_name="application_id"
    )
    op.alter_column("claim", "laa_reference", new_column_name="application_id")
    op.alter_column("history_event", "laa_reference", new_column_name="application_id")


def downgrade() -> None:
    op.alter_column("history_event", "application_id", new_column_name="laa_reference")
    op.alter_column("claim", "application_id", new_column_name="laa_reference")
    op.alter_column(
        "application_public_body", "application_id", new_column_name="laa_reference"
    )
    op.alter_column(
        "application_proceeding", "application_id", new_column_name="laa_reference"
    )
    op.alter_column("application", "application_id", new_column_name="laa_reference")
