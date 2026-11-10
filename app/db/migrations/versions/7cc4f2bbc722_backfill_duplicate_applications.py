"""backfill duplicate applications

Revision ID: 7cc4f2bbc722
Revises: idds_709_forecast_report_type
Create Date: 2026-11-03 14:59:17.597971

"""
from typing import Sequence, Union

from alembic import op
from app.adapters.application_repository_adapter import ApplicationRepositoryAdapter
from app.models.application.index import DuplicateApplicationRecord
from app.models.application.index import Application
import sqlalchemy as sa
import sqlmodel
from sqlmodel import select
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7cc4f2bbc722'
down_revision: Union[str, None] = 'idds_709_forecast_report_type'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def backfill_duplicate_applications(session: sqlmodel.Session) -> None:
    """Create missing duplicate records for every application."""
    repository = ApplicationRepositoryAdapter(session)

    existing_pairs: set[tuple[int, int]] = set(
        session.exec(
            select(
                DuplicateApplicationRecord.application_id,
                DuplicateApplicationRecord.duplicate_application_id,
            )
        ).all()
    )

    all_application_ids = session.exec(
        select(Application.application_id).order_by(Application.created_at)
    ).all()

    for application_id in all_application_ids:
        potential_duplicates = repository.identify_duplicates(application_id)

        new_duplicate_ids = [
            duplicate_id
            for duplicate_id in potential_duplicates
            if (application_id, duplicate_id) not in existing_pairs and (duplicate_id, application_id) not in existing_pairs
        ]

        repository.create_duplicate_records(application_id, new_duplicate_ids)
        existing_pairs.update((application_id, duplicate_id) for duplicate_id in new_duplicate_ids)

    return

def upgrade() -> None:
    session = sqlmodel.Session(bind=op.get_bind())
    backfill_duplicate_applications(session)
    session.commit()


def downgrade() -> None:
    # Can't distinguish backfilled data from original data, so we won't attempt to remove it
    pass