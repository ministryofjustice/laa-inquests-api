"""
IDDS-429 Adding new proceeding ids to the enum type proceedingid

Revision ID: fc72a3f74810
Revises: e8f6a1c2d4b0
Create Date: 2026-07-28 11:52:42.087194

"""

from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "fc72a3f74810"
down_revision: Union[str, None] = "e8f6a1c2d4b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

old_proceeding_ids = [
    "IQ001",
    "IQ002",
    "IQ003",
    "IQ004",
    "IQ010",
    "MH028",
    "MH030",
    "MN035",
    "MN036",
    "PC049",
    "TEST1",
]
new_proceeding_ids = [
    "IQ001",
    "IQ002",
    "IQ003",
    "IQ004",
    "IQ010",
    "IQCA",
    "IQCC",
    "IQDV",
    "IQED",
    "IQHO",
    "IQMC",
    "IQMH",
    "IQMT",
    "IQOT",
    "IQPC",
    "IQPO",
    "IQTR",
    "MH028",
    "MH030",
    "MN035",
    "MN036",
    "PC049",
    "TEST1",
]


def upgrade() -> None:
    op.sync_enum_values(
        "public",
        "proceedingid",
        old_proceeding_ids,
        new_proceeding_ids,
        [("application_proceeding", "proceeding_id"), ("proceeding", "proceeding_id")],
        False,
    )


def downgrade() -> None:
    op.sync_enum_values(
        "public",
        "proceedingid",
        new_proceeding_ids,
        old_proceeding_ids,
        [("application_proceeding", "proceeding_id"), ("proceeding", "proceeding_id")],
        True,
    )
