"""IDDS-1256 add office id to claim evidence

Revision ID: idds_1256_evidence_office_id
Revises: idds_1256_letter_office_id
Create Date: 2026-11-20 09:52:16.205079

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "idds_1256_evidence_office_id"
down_revision: str | None = "idds_1256_letter_office_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# One-off owner for evidence not attached to any claim. Not a default for new uploads.
UNATTACHED_EVIDENCE_OFFICE_ID = "0U651L"


def upgrade() -> None:
    op.add_column(
        "claim_evidence",
        sa.Column("office_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )

    op.execute(
        """
        UPDATE claim_evidence
        SET office_id = provider.office_id
        FROM claim
        JOIN application ON application.application_id = claim.application_id
        JOIN provider ON provider.provider_id = application.provider_id
        WHERE claim_evidence.claim_id = claim.claim_id
        """
    )

    # Cost templates reference evidence by file id only. A file referenced by
    # several claims takes the office of the lowest claim_id.
    op.execute(
        """
        UPDATE claim_evidence
        SET office_id = owner.office_id
        FROM (
            SELECT DISTINCT ON (claim_cost_template.claim_cost_template_file_id)
                claim_cost_template.claim_cost_template_file_id,
                provider.office_id
            FROM claim_cost_template
            JOIN claim ON claim.claim_id = claim_cost_template.claim_id
            JOIN application ON application.application_id = claim.application_id
            JOIN provider ON provider.provider_id = application.provider_id
            ORDER BY
                claim_cost_template.claim_cost_template_file_id,
                claim_cost_template.claim_id
        ) AS owner
        WHERE claim_evidence.office_id IS NULL
          AND claim_evidence.claim_evidence_id = owner.claim_cost_template_file_id
        """
    )

    connection = op.get_bind()
    unresolved_attached = connection.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM claim_evidence
            WHERE office_id IS NULL
              AND (
                  claim_id IS NOT NULL
                  OR EXISTS (
                      SELECT 1 FROM claim_cost_template
                      WHERE claim_cost_template.claim_cost_template_file_id
                          = claim_evidence.claim_evidence_id
                  )
              )
            """
        )
    ).scalar_one()
    if unresolved_attached:
        raise RuntimeError(
            f"{unresolved_attached} attached claim_evidence rows have no provider office id"
        )

    connection.execute(
        sa.text(
            "UPDATE claim_evidence SET office_id = :office_id WHERE office_id IS NULL"
        ),
        {"office_id": UNATTACHED_EVIDENCE_OFFICE_ID},
    )

    op.alter_column(
        "claim_evidence",
        "office_id",
        existing_type=sqlmodel.sql.sqltypes.AutoString(),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("claim_evidence", "office_id")
