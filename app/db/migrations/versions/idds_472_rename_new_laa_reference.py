"""Rename new_laa_reference to laa_reference.

Revision ID: idds_472_laa_reference
Revises: 85739150dcc5
Create Date: 2026-09-04

"""
from typing import Sequence, Union

from alembic import op


revision: str = "idds_472_laa_reference"
down_revision: Union[str, None] = "85739150dcc5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("application", "new_laa_reference", new_column_name="laa_reference")

    # Update existing history events with the new laa_reference value
    op.execute(
        """
        UPDATE history_event
        SET event_data = jsonb_set(to_jsonb(event_data), '{laa_reference}', to_jsonb(application.laa_reference))
        FROM application
        WHERE history_event.event_reference = 'CERTIFICATE_CREATED'
        AND history_event.application_id = application.application_id
        """
    )


def downgrade() -> None:
    op.alter_column("application", "laa_reference", new_column_name="new_laa_reference")

    # Downgrade existing history events to use the old laa_reference value
    op.execute(
        """
        UPDATE history_event
        SET event_data = jsonb_set(to_jsonb(event_data), '{laa_reference}', to_jsonb(application.application_id))
        FROM application
        WHERE history_event.event_reference = 'CERTIFICATE_CREATED'
        AND history_event.application_id = application.application_id
        """
    )
