"""update substantive cost limitation to 10,000

Revision ID: 9b2ae8ea620f
Revises: 02a055ebbdc7
Create Date: 2026-07-08 14:54:40.096685

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "9b2ae8ea620f"
down_revision: Union[str, None] = "02a055ebbdc7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE proceeding SET substantive_cost_limitation = 10000")


def downgrade() -> None:
    op.execute("UPDATE proceeding SET substantive_cost_limitation = 25000")
