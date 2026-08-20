"""repoint_bad_providers_and_cleanup

Revision ID: 576bb7f74f01
Revises: 4d7c2a91b6ef
Create Date: 2026-07-22 10:39:12.823149

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "576bb7f74f01"
down_revision: Union[str, None] = "4d7c2a91b6ef"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()

    bad_office_id = "001"

    good_provider_id = connection.execute(
        sa.text(
            """
            SELECT provider_id
            FROM provider
            WHERE NOT (
                office_id = :bad_office_id
            )
            ORDER BY provider_id DESC
            LIMIT 1
            """
        ),
        {"bad_office_id": bad_office_id},
    ).scalar_one_or_none()

    if good_provider_id is None:
        return

    connection.execute(
        sa.text(
            """
            UPDATE application
            SET provider_id = :target_provider_id
            WHERE provider_id IN (
                SELECT provider_id
                FROM provider
                WHERE office_id = :bad_office_id
            )
            """
        ),
        {"target_provider_id": good_provider_id, "bad_office_id": bad_office_id},
    )

    connection.execute(
        sa.text(
            """
            DELETE FROM provider p
            WHERE p.office_id = :bad_office_id
              AND NOT EXISTS (
                  SELECT 1
                  FROM application a
                  WHERE a.provider_id = p.provider_id
              )
            """
        ),
        {"bad_office_id": bad_office_id},
    )


def downgrade() -> None:
    # Data migration is intentionally irreversible.
    return None
