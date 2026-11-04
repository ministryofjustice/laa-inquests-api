from datetime import UTC, date, datetime
from decimal import Decimal

from sqlmodel import select

from app.adapters.claim_repository_adapter import ClaimRepositoryAdapter
from app.models.application.enums import MeritsDecision, PublicBodyId
from app.models.application.index import (
    Application,
    ApplicationPublicBody,
    Proceeding,
)
from app.models.claim.enums import ClaimStatus, ClaimType
from tests.e2e.factories import create_application_in_db, create_claim_in_db

EFFECTIVE_FROM = date(2026, 1, 1)
EFFECTIVE_TO = date(2026, 12, 31)


def _certified_application(
    session,
    laa_reference: str,
    effective_date: date | None,
    *,
    bodies: tuple[PublicBodyId, ...] = (PublicBodyId.HOME_OFFICE,),
    end_date: date | None = None,
    merits_decision: MeritsDecision = MeritsDecision.GRANTED,
) -> Application:
    return create_application_in_db(
        session,
        laa_reference=laa_reference,
        status="LIVE",
        public_bodies=[ApplicationPublicBody(public_body_id=body) for body in bodies],
        proceeding_overrides={
            "merits_decision": merits_decision,
            "certificate_start_date": effective_date,
            "certificate_end_date": end_date,
        },
    )


def _candidates(session, effective_from=EFFECTIVE_FROM, effective_to=EFFECTIVE_TO):
    return list(
        ClaimRepositoryAdapter(session).iter_forecast_candidates(
            effective_from, effective_to
        )
    )


def test_iter_forecast_candidates_maps_certificate_fields(session):
    _certified_application(
        session,
        "INQ-111-111",
        date(2026, 3, 15),
        end_date=date(2030, 1, 1),
        merits_decision=MeritsDecision.GRANTED,
    )

    [candidate] = _candidates(session)

    assert candidate.laa_reference == "INQ-111-111"
    assert candidate.application_status == "LIVE"
    assert candidate.merits_decision == MeritsDecision.GRANTED
    assert candidate.certificate_effective_date == date(2026, 3, 15)
    assert candidate.certificate_end_date == date(2030, 1, 1)
    assert candidate.public_bodies == (PublicBodyId.HOME_OFFICE,)
    assert candidate.claims == ()


def test_iter_forecast_candidates_uses_the_proceeding_cost_limitation(session):
    _certified_application(session, "INQ-111-111", date(2026, 3, 15))
    proceeding = session.exec(select(Proceeding)).one()
    proceeding.substantive_cost_limitation = 25000
    session.add(proceeding)
    session.commit()

    [candidate] = _candidates(session)

    assert candidate.cost_limit == 25000


def test_iter_forecast_candidates_filters_on_inclusive_effective_date_range(session):
    _certified_application(session, "INQ-000-001", date(2026, 1, 1))
    _certified_application(session, "INQ-000-002", date(2026, 12, 31))
    _certified_application(session, "INQ-000-003", date(2025, 12, 31))
    _certified_application(session, "INQ-000-004", date(2027, 1, 1))
    _certified_application(session, "INQ-000-005", None)

    assert [c.laa_reference for c in _candidates(session)] == [
        "INQ-000-001",
        "INQ-000-002",
    ]


def test_iter_forecast_candidates_does_not_decide_eligibility(session):
    _certified_application(
        session,
        "INQ-000-001",
        date(2026, 3, 1),
        merits_decision=MeritsDecision.REFUSED,
        end_date=date(2020, 1, 1),
    )

    assert [c.laa_reference for c in _candidates(session)] == ["INQ-000-001"]


def test_iter_forecast_candidates_orders_by_effective_date_then_reference(session):
    _certified_application(session, "INQ-000-003", date(2026, 5, 1))
    _certified_application(session, "INQ-000-002", date(2026, 2, 1))
    _certified_application(session, "INQ-000-009", date(2026, 2, 1))
    _certified_application(session, "INQ-000-001", date(2026, 2, 1))

    assert [c.laa_reference for c in _candidates(session)] == [
        "INQ-000-001",
        "INQ-000-002",
        "INQ-000-009",
        "INQ-000-003",
    ]


def test_iter_forecast_candidates_returns_every_public_body_without_duplicating(
    session,
):
    _certified_application(
        session,
        "INQ-000-001",
        date(2026, 3, 1),
        bodies=(PublicBodyId.MINISTRY_OF_JUSTICE, PublicBodyId.CABINET_OFFICE),
    )
    _certified_application(session, "INQ-000-002", date(2026, 3, 2))

    candidates = _candidates(session)

    assert len(candidates) == 2
    assert set(candidates[0].public_bodies) == {
        PublicBodyId.MINISTRY_OF_JUSTICE,
        PublicBodyId.CABINET_OFFICE,
    }
    assert candidates[1].public_bodies == (PublicBodyId.HOME_OFFICE,)


def test_iter_forecast_candidates_returns_the_claims_of_each_application(session):
    first = _certified_application(session, "INQ-000-001", date(2026, 3, 1))
    second = _certified_application(session, "INQ-000-002", date(2026, 3, 2))
    create_claim_in_db(
        session,
        application_id=first.application_id,
        status=ClaimStatus.PAY_IN_FULL,
        claim_type=ClaimType.FINAL_BILL,
        total_profit_cost_gross="1200.50",
        total_profit_cost_vat_zero="0.00",
        submission_date=datetime(2026, 4, 1, tzinfo=UTC),
    )
    create_claim_in_db(
        session,
        application_id=first.application_id,
        status=ClaimStatus.REJECTED,
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        total_profit_cost_gross="10.00",
        total_profit_cost_vat_zero="5.00",
    )
    create_claim_in_db(
        session,
        application_id=second.application_id,
        status=ClaimStatus.SUBMITTED,
        total_profit_cost_gross="75.00",
    )

    first_candidate, second_candidate = _candidates(session)

    assert {
        (claim.claim_type, claim.status, claim.gross, claim.vat_zero_total)
        for claim in first_candidate.claims
    } == {
        (
            ClaimType.FINAL_BILL,
            ClaimStatus.PAY_IN_FULL,
            Decimal("1200.50"),
            Decimal("0.00"),
        ),
        (
            ClaimType.PAYMENT_ON_ACCOUNT,
            ClaimStatus.REJECTED,
            Decimal("10.00"),
            Decimal("5.00"),
        ),
    }
    assert [claim.status for claim in second_candidate.claims] == [
        ClaimStatus.SUBMITTED
    ]


def test_iter_forecast_candidates_ignores_claims_of_applications_outside_the_range(
    session,
):
    inside = _certified_application(session, "INQ-000-001", date(2026, 3, 1))
    outside = _certified_application(session, "INQ-000-002", date(2027, 3, 1))
    create_claim_in_db(session, application_id=inside.application_id)
    create_claim_in_db(session, application_id=outside.application_id)

    [candidate] = _candidates(session)

    assert len(candidate.claims) == 1
