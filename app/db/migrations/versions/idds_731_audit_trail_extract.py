"""IDDS-731 user audit trail extract

Adds the AUDIT_TRAIL report type, the history_event.actor_email_address column
and the timestamp indexes the cross-case audit trail query filters on.

Revision ID: idds_731_audit_trail_extract
Revises: 98afb9a716c2
Create Date: 2026-10-26 16:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "idds_731_audit_trail_extract"
down_revision: str | None = "98afb9a716c2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REPORT_TYPES_BEFORE = ["APPLICATIONS_BACKLOG", "CLAIMS_BACKLOG", "PAYMENT_EXTRACT"]
REPORT_TYPES_AFTER = [
    "APPLICATIONS_BACKLOG",
    "AUDIT_TRAIL",
    "CLAIMS_BACKLOG",
    "PAYMENT_EXTRACT",
]


def upgrade() -> None:
    op.sync_enum_values(
        "public",
        "reporttype",
        REPORT_TYPES_BEFORE,
        REPORT_TYPES_AFTER,
        [("report_audit_event", "report_type")],
        False,
    )
    # Null for events recorded before the email was stored: there is nothing to backfill from.
    op.add_column(
        "history_event",
        sa.Column(
            "actor_email_address", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
    )
    op.create_index("ix_history_event_timestamp", "history_event", ["timestamp"])
    op.create_index(
        "ix_report_audit_event_timestamp", "report_audit_event", ["timestamp"]
    )


def downgrade() -> None:
    op.drop_index("ix_report_audit_event_timestamp", table_name="report_audit_event")
    op.drop_index("ix_history_event_timestamp", table_name="history_event")
    op.drop_column("history_event", "actor_email_address")
    # Fails if audit trail report downloads have been recorded, rather than deleting audit rows.
    op.sync_enum_values(
        "public",
        "reporttype",
        REPORT_TYPES_AFTER,
        REPORT_TYPES_BEFORE,
        [("report_audit_event", "report_type")],
        True,
    )
