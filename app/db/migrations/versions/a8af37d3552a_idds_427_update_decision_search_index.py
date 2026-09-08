"""IDDS-427-update-decision-search-index

Revision ID: a8af37d3552a
Revises: 4a69570166d5
Create Date: 2026-09-08 09:58:54.362701

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a8af37d3552a"
down_revision: Union[str, None] = "4a69570166d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # search_applications joins on application_id (from a unique laa_reference match) then
    # optionally filters merits_decision, so application_id must lead the composite index.
    op.create_index(
        "ix_application_proceeding_application_id_merits_decision",
        "application_proceeding",
        ["application_id", "merits_decision"],
        unique=False,
    )
    op.create_index(
        "ix_claim_type_id_status_id_submission_date",
        "claim",
        ["claim_type_id", "status_id", "submission_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_claim_type_id_status_id_submission_date",
        table_name="claim",
    )
    op.drop_index(
        "ix_application_proceeding_application_id_merits_decision",
        table_name="application_proceeding",
    )