"""IDDS-876 add claim evidence file size

Revision ID: idds_876_evidence_file_size
Revises: idds_597_cpe_created_at_idx
Create Date: 2026-10-08 11:27:19.236490

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "idds_876_evidence_file_size"
down_revision: str | None = "idds_597_cpe_created_at_idx"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("claim_evidence", sa.Column("file_size", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("claim_evidence", "file_size")
