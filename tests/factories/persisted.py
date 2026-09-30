"""Session-backed factories: ``build_*(for_db=True)`` plus commit and refresh."""

from collections.abc import Iterable

from sqlmodel import Session, select

from app.models.application.index import (
    Application,
    CoronersLetter,
    Proceeding,
    ProceedingId,
)
from app.models.claim.enums import InquestOutcomeCode
from app.models.claim.index import (
    Claim,
    ClaimCostTemplate,
    ClaimDecision,
    ClaimEvidence,
    ClaimInquestOutcome,
    ClaimPaymentExtract,
)
from app.models.history.index import HistoryEvent
from tests.factories import builders


def _persist(session: Session, obj):
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def _application_id(application: Application | int) -> int:
    if isinstance(application, int):
        return application
    return application.application_id


def _claim_id(claim: Claim | int) -> int:
    if isinstance(claim, int):
        return claim
    return claim.claim_id


def application_by_reference(session: Session, laa_reference: str) -> Application:
    return session.exec(
        select(Application).where(Application.laa_reference == laa_reference)
    ).one()


def create_application(
    session: Session, *, substantive_cost_limitation: int | None = None, **kwargs
) -> Application:
    """Accepts the same kwargs as ``build_application``.

    ``substantive_cost_limitation`` gives the application its own Proceeding row so the
    seeded IQOT limit is left alone.
    """
    if substantive_cost_limitation is not None:
        proceeding = _create_dedicated_proceeding(session, substantive_cost_limitation)
        kwargs["proceeding_overrides"] = {
            "proceeding_id": proceeding.proceeding_id
        } | kwargs.get("proceeding_overrides", {})
    return _persist(session, builders.build_application(for_db=True, **kwargs))


def _create_dedicated_proceeding(session: Session, limit: int) -> Proceeding:
    taken = set(session.exec(select(Proceeding.proceeding_id)).all())
    unused = next((pid for pid in ProceedingId if pid not in taken), None)
    if unused is None:
        raise RuntimeError("No unused ProceedingId left for a dedicated Proceeding")
    return _persist(
        session,
        builders.build_proceeding(
            proceeding_id=unused, substantive_cost_limitation=limit
        ),
    )


def create_coroners_letter(session: Session, **overrides) -> CoronersLetter:
    return _persist(session, builders.build_coroners_letter(**overrides))


def create_claim(
    session: Session,
    application: Application | int,
    *,
    preset=builders.build_claim,
    **overrides,
) -> Claim:
    """``preset`` is any ``build_*claim`` builder, e.g. ``builders.build_poa_claim``."""
    return _persist(
        session,
        preset(application_id=_application_id(application), for_db=True, **overrides),
    )


def create_claim_evidence(
    session: Session, claim: Claim | None = None, **overrides
) -> ClaimEvidence:
    if claim is not None:
        overrides["claim_id"] = claim.claim_id
    return _persist(session, builders.build_claim_evidence(**overrides))


def create_claim_decision(
    session: Session,
    claim: Claim | int,
    *,
    reasons: Iterable[dict] = (),
    **overrides,
) -> ClaimDecision:
    """``reasons`` is an iterable of ``build_decision_reason`` override dicts."""
    decision = _persist(
        session, builders.build_claim_decision(claim_id=_claim_id(claim), **overrides)
    )
    for reason in reasons:
        _persist(
            session,
            builders.build_decision_reason(
                claim_decision_id=decision.claim_decision_id, **reason
            ),
        )
    session.refresh(decision)
    return decision


def create_claim_inquest_outcomes(
    session: Session, claim: Claim | int, outcomes: Iterable[InquestOutcomeCode]
) -> list[ClaimInquestOutcome]:
    return [
        _persist(
            session,
            builders.build_claim_inquest_outcome(
                claim_id=_claim_id(claim), inquest_outcome_id=outcome
            ),
        )
        for outcome in outcomes
    ]


def create_claim_cost_template(
    session: Session, claim: Claim | int, **overrides
) -> ClaimCostTemplate:
    return _persist(
        session,
        builders.build_claim_cost_template(claim_id=_claim_id(claim), **overrides),
    )


def create_payment_extracts(
    session: Session,
    claim: Claim | int,
    extracts: Iterable[dict] = ({}, {}),
) -> list[ClaimPaymentExtract]:
    """One extract line per dict of ``build_claim_payment_extract`` overrides."""
    return [
        _persist(
            session,
            builders.build_claim_payment_extract(
                claim_id=_claim_id(claim), sequence_number=sequence, **extract
            ),
        )
        for sequence, extract in enumerate(extracts, start=1)
    ]


def create_history_event(
    session: Session, application: Application | int, **overrides
) -> HistoryEvent:
    return _persist(
        session,
        builders.build_history_event(
            application_id=_application_id(application), **overrides
        ),
    )
