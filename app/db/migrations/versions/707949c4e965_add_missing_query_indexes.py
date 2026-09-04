"""Add missing query indexes

Revision ID: 707949c4e965
Revises: d2aca39c7115
Create Date: 2026-09-03 16:22:05.349774

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "707949c4e965"
down_revision: str | None = "d2aca39c7115"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_application_proceeding_merits_decision_laa_reference",
        "application_proceeding",
        ["merits_decision", "laa_reference"],
        unique=False,
    )
    op.create_index("ix_claim_laa_reference", "claim", ["laa_reference"], unique=False)
    op.create_index(
        "ix_claim_status_id_submission_date",
        "claim",
        ["status_id", "submission_date"],
        unique=False,
    )
    op.create_index(
        "ix_claim_decision_claim_id",
        "claim_decision",
        ["claim_id"],
        unique=False,
    )
    op.create_index(
        "ix_history_event_laa_reference_timestamp",
        "history_event",
        ["laa_reference", "timestamp"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_history_event_laa_reference_timestamp", table_name="history_event"
    )
    op.drop_index("ix_claim_decision_claim_id", table_name="claim_decision")
    op.drop_index("ix_claim_status_id_submission_date", table_name="claim")
    op.drop_index("ix_claim_laa_reference", table_name="claim")
    op.drop_index(
        "ix_application_proceeding_merits_decision_laa_reference",
        table_name="application_proceeding",
    )
