"""idds_287_update_proceeding_descriptions

Revision ID: 82b97fef429d
Revises: dee9bbd3102e
Create Date: 2026-07-22 11:00:08.532294

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "82b97fef429d"
down_revision: Union[str, None] = "dee9bbd3102e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE proceeding
        SET proceeding_description =
            'To be represented on an application for a ' || proceeding_name
        WHERE proceeding_name IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE proceeding
        SET proceeding_description = proceeding_name
        WHERE proceeding_name IS NOT NULL
        """
    )
