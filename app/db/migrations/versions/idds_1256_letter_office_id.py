"""IDDS-1256 add office id to coroners letter

Revision ID: idds_1256_letter_office_id
Revises: idds_1086_replace_proceedings
Create Date: 2026-11-18 14:37:39.504157

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "idds_1256_letter_office_id"
down_revision: str | None = "idds_1086_replace_proceedings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# One-off owner for letters not attached to any application. Not a default for new uploads.
UNATTACHED_LETTER_OFFICE_ID = "0U651L"


def upgrade() -> None:
    op.add_column(
        "coroners_letter",
        sa.Column("office_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )

    # A letter shared by several applications takes the office of the lowest application_id.
    op.execute(
        """
        UPDATE coroners_letter
        SET office_id = owner.office_id
        FROM (
            SELECT DISTINCT ON (application.coroners_letter_id)
                application.coroners_letter_id,
                provider.office_id
            FROM application
            JOIN provider ON provider.provider_id = application.provider_id
            WHERE application.coroners_letter_id IS NOT NULL
            ORDER BY application.coroners_letter_id, application.application_id
        ) AS owner
        WHERE coroners_letter.coroners_letter_id = owner.coroners_letter_id
        """
    )

    connection = op.get_bind()
    unresolved_attached = connection.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM coroners_letter
            WHERE office_id IS NULL
              AND EXISTS (
                  SELECT 1 FROM application
                  WHERE application.coroners_letter_id = coroners_letter.coroners_letter_id
              )
            """
        )
    ).scalar_one()
    if unresolved_attached:
        raise RuntimeError(
            f"{unresolved_attached} attached coroners_letter rows have no provider office id"
        )

    connection.execute(
        sa.text(
            "UPDATE coroners_letter SET office_id = :office_id WHERE office_id IS NULL"
        ),
        {"office_id": UNATTACHED_LETTER_OFFICE_ID},
    )

    op.alter_column(
        "coroners_letter",
        "office_id",
        existing_type=sqlmodel.sql.sqltypes.AutoString(),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("coroners_letter", "office_id")
