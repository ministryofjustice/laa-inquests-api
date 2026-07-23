"""rename claim status pending to submitted

Revision ID: c235530a87b5
Revises: 82b97fef429d
Create Date: 2026-07-23 11:09:03.393942

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c235530a87b5"
down_revision: Union[str, None] = "82b97fef429d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE claimstatus RENAME VALUE 'PENDING' TO 'SUBMITTED'")


def downgrade() -> None:
    op.execute("ALTER TYPE claimstatus RENAME VALUE 'SUBMITTED' TO 'PENDING'")
