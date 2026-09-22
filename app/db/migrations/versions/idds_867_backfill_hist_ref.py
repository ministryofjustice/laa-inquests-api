"""Backfill claim_reference into claim history event_data

Populates ``claim_reference`` in ``event_data`` for existing
``CLAIM_SUBMITTED`` and ``CLAIM_ASSESSMENT_COMPLETED`` history events that were
persisted before the reference was recorded. The reference is derived from the
related claim and only applied when it can be resolved unambiguously (exactly
one claim of the event's ``claim_type`` exists for the application). Ambiguous
events are left untouched; the UI degrades gracefully when the field is absent.

Revision ID: idds_867_backfill_hist_ref
Revises: idds_796_claim_reference
Create Date: 2026-09-22 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy.orm import Session

from app.models.claim.index import Claim
from app.models.history.enums import HistoryEventReference
from app.models.history.index import HistoryEvent

# revision identifiers, used by Alembic.
revision: str = "idds_867_backfill_hist_ref"
down_revision: Union[str, None] = "idds_796_claim_reference"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CLAIM_EVENT_REFERENCES = (
    HistoryEventReference.CLAIM_SUBMITTED,
    HistoryEventReference.CLAIM_ASSESSMENT_COMPLETED,
)


def _claim_type_key(claim_type: object) -> object:
    """Normalise a claim type (enum or raw string) to its comparable value."""
    return getattr(claim_type, "value", claim_type)


def _build_claim_index(
    claims: list[tuple[int, object, str]],
) -> dict[tuple[int, object], list[str]]:
    index: dict[tuple[int, object], list[str]] = {}
    for application_id, claim_type, claim_reference in claims:
        index.setdefault((application_id, _claim_type_key(claim_type)), []).append(
            claim_reference
        )
    return index


def _select_claim_reference(
    claim_type: object,
    application_id: int,
    claim_index: dict[tuple[int, object], list[str]],
) -> str | None:
    """Return the claim reference only when it can be resolved unambiguously."""
    references = claim_index.get((application_id, _claim_type_key(claim_type)))
    if references and len(references) == 1:
        return references[0]
    return None


def backfill_history_claim_references(session: Session) -> int:
    """Populate ``claim_reference`` in claim history ``event_data``.

    Returns the number of events updated.
    """
    claims = session.query(Claim).all()
    claim_index = _build_claim_index(
        [(claim.application_id, claim.claim_type_id, claim.claim_reference) for claim in claims]
    )

    events = (
        session.query(HistoryEvent)
        .filter(HistoryEvent.event_reference.in_(CLAIM_EVENT_REFERENCES))
        .all()
    )

    updated = 0
    for event in events:
        data = event.event_data
        if not data or data.get("claim_reference"):
            continue
        claim_type = data.get("claim_type")
        if claim_type is None:
            continue
        claim_reference = _select_claim_reference(
            claim_type, event.application_id, claim_index
        )
        if claim_reference is None:
            continue
        event.event_data = {**data, "claim_reference": claim_reference}
        updated += 1

    session.flush()
    return updated


def upgrade() -> None:
    session = Session(bind=op.get_bind())
    backfill_history_claim_references(session)
    session.commit()


def downgrade() -> None:
    # The reference is additive metadata inside a shared JSON column; removing it
    # for only the backfilled events cannot be done safely, so this is a no-op.
    pass
