"""IDDS-796 add claim_reference field to claim

Revision ID: idds_796_claim_reference
Revises: 696fce63e2b7
Create Date: 2026-09-21 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.adapters.claim_repository_adapter import ClaimRepositoryAdapter

# revision identifiers, used by Alembic.
revision: str = "idds_796_claim_reference"
down_revision: Union[str, None] = "696fce63e2b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Add the column as nullable
    op.add_column(
        "claim",
        sa.Column(
            "claim_reference",
            sqlmodel.sql.sqltypes.AutoString(length=14),
            nullable=True,
        ),
    )

    # Step 2: Backfill claim_reference for all existing claims
    bind = op.get_bind()
    session = Session(bind=bind)
    adapter = ClaimRepositoryAdapter(session)

    claim_ids = session.scalars(
        text("SELECT claim_id FROM claim WHERE claim_reference IS NULL")
    ).all()

    for claim_id in claim_ids:
        session.execute(
            text(
                "UPDATE claim SET claim_reference = :claim_reference "
                "WHERE claim_id = :claim_id"
            ),
            {
                "claim_reference": adapter._get_claim_reference(),
                "claim_id": claim_id,
            },
        )

    session.commit()

    # Step 3: Make the column NOT NULL
    op.alter_column("claim", "claim_reference", nullable=False)

    # Step 4: Add unique constraint
    op.create_unique_constraint(
        "uq_claim_claim_reference", "claim", ["claim_reference"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_claim_claim_reference", "claim", type_="unique")
    op.drop_column("claim", "claim_reference")
