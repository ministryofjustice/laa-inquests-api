"""idds_287_add_proceeding_name

Revision ID: 4d7c2a91b6ef
Revises: 59ab5b5eacce
Create Date: 2026-07-20 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = "4d7c2a91b6ef"
down_revision: Union[str, None] = "59ab5b5eacce"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "proceeding",
        sa.Column("proceeding_name", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.execute("UPDATE proceeding SET proceeding_name = proceeding_description")


def downgrade() -> None:
    op.drop_column("proceeding", "proceeding_name")
