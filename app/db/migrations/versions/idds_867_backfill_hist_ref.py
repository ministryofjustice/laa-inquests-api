"""Backfill claim_reference into claim history event_data

Populates ``claim_reference`` in ``event_data`` for existing
``CLAIM_SUBMITTED`` and ``CLAIM_ASSESSMENT_COMPLETED`` history events that were
persisted before the reference was recorded.

The reference is derived from the related claim, matched on
``application_id`` + ``claim_type`` (the only identifying fields present in
historic ``event_data``). Since an application can have several claims of the
same type, matches are disambiguated by nearest timestamp: history events are
created in the same transaction as the claim (for ``CLAIM_SUBMITTED``, compared
against ``claim.submission_date``) or its decision (for
``CLAIM_ASSESSMENT_COMPLETED``, compared against ``claim_decision.created_at``
for a decision matching the event's recorded ``claim_decision``). If two
candidate claims are equally close, the event is left untouched; the UI
degrades gracefully when the field is absent.

Revision ID: idds_867_backfill_hist_ref
Revises: idds_796_claim_reference
Create Date: 2026-09-22 00:00:00.000000

"""

from datetime import datetime
from typing import Sequence, Union

from alembic import op
from sqlalchemy.orm import Session

from app.models.claim.index import Claim, ClaimDecision
from app.models.history.enums import HistoryEventReference
from app.models.history.index import HistoryEvent

# revision identifiers, used by Alembic.
revision: str = "idds_867_backfill_hist_ref"
down_revision: Union[str, None] = "idds_796_claim_reference"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Historic CLAIM_ASSESSMENT_COMPLETED event_data uses ClaimStatus values, while
# claim_decision.decision uses ClaimDecisionStatus values. Only maps the values
# that use_cases actually emit into event_data.
DECISION_STATUS_ALIASES = {"REJECTED": "REJECT"}


def _enum_key(value: object) -> object:
    """Normalise an enum (or raw string) to its comparable value."""
    return getattr(value, "value", value)


def _normalize_decision_status(value: object) -> object:
    key = _enum_key(value)
    return DECISION_STATUS_ALIASES.get(key, key)


def _pick_nearest(
    candidates: list[tuple[str, datetime]], event_time: datetime
) -> str | None:
    """Return the claim reference closest in time, or None if ambiguous."""
    if not candidates:
        return None
    diffs = [
        (abs((timestamp - event_time).total_seconds()), reference)
        for reference, timestamp in candidates
    ]
    min_distance = min(dist for dist, _ in diffs)
    nearest_references = {ref for dist, ref in diffs if dist == min_distance}
    if len(nearest_references) == 1:
        return nearest_references.pop()
    raise ValueError("Ambiguous nearest claim reference")


def _build_submitted_index(
    claims: list[Claim],
) -> dict[tuple[int, object], list[tuple[str, datetime]]]:
    index: dict[tuple[int, object], list[tuple[str, datetime]]] = {}
    for claim in claims:
        key = (claim.application_id, _enum_key(claim.claim_type_id))
        index.setdefault(key, []).append((claim.claim_reference, claim.submission_date))
    return index


def _build_assessment_index(
    claims: list[Claim],
    decisions: list[ClaimDecision],
) -> dict[tuple[int, object, object], list[tuple[str, datetime]]]:
    claims_by_id = {claim.claim_id: claim for claim in claims}
    index: dict[tuple[int, object, object], list[tuple[str, datetime]]] = {}
    for decision in decisions:
        claim = claims_by_id.get(decision.claim_id)
        if claim is None or decision.created_at is None:
            continue
        key = (
            claim.application_id,
            _enum_key(claim.claim_type_id),
            _normalize_decision_status(decision.decision),
        )
        index.setdefault(key, []).append((claim.claim_reference, decision.created_at))
    return index


def backfill_history_claim_references(session: Session) -> int:
    """Populate ``claim_reference`` in claim history ``event_data``.

    Returns the number of events updated.
    """
    claims = session.query(Claim).all()
    submitted_index = _build_submitted_index(claims)
    assessment_index = _build_assessment_index(
        claims, session.query(ClaimDecision).all()
    )

    events = (
        session.query(HistoryEvent)
        .filter(
            HistoryEvent.event_reference.in_(
                (
                    HistoryEventReference.CLAIM_SUBMITTED,
                    HistoryEventReference.CLAIM_ASSESSMENT_COMPLETED,
                )
            )
        )
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

        if event.event_reference == HistoryEventReference.CLAIM_SUBMITTED:
            candidates = submitted_index.get(
                (event.application_id, _enum_key(claim_type)), []
            )
        else:
            decision_status = data.get("claim_decision")
            if decision_status is None:
                continue
            candidates = assessment_index.get(
                (
                    event.application_id,
                    _enum_key(claim_type),
                    _normalize_decision_status(decision_status),
                ),
                [],
            )

        claim_reference = _pick_nearest(candidates, event.timestamp)
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
