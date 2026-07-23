from decimal import Decimal

from sqlmodel import select

from app.adapters.claim_repository_adapter import ClaimRepositoryAdapter
from app.domain.claim import Claim as DomainClaim
from app.models.application.index import Application
from app.models.claim.enums import (
    ClaimDecisionStatus,
    ClaimStatus,
    ClaimType,
    POAType,
    ReasonCode,
)
from app.models.claim.index import Claim, ClaimDecision, DecisionReason


def _make_domain_claim(overrides=None) -> DomainClaim:
    payload = {
        "claim_type": ClaimType.PAYMENT_ON_ACCOUNT,
        "net": Decimal("1000.00"),
        "gross": Decimal("1200.00"),
        "vat_zero_total": None,
        "poa_type": POAType.PROFIT_COST,
    }
    if overrides is not None:
        payload.update(overrides)
    return DomainClaim(**payload)


def _create_claim(session, laa_reference) -> Claim:
    adapter = ClaimRepositoryAdapter(session)
    return adapter.create_claim(
        str(laa_reference), _make_domain_claim(), "claimant@example.com"
    )


# --- create_claim ---


def test_create_claim_persists_claim_with_expected_values(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = ClaimRepositoryAdapter(session)

    created = adapter.create_claim(
        str(laa_reference),
        _make_domain_claim(
            {"poa_type": POAType.EXPERT_COST, "vat_zero_total": Decimal("150.00")}
        ),
        "claimant-123@provider.co.uk",
    )
    stored = session.get(Claim, created.claim_id)

    assert created.claim_id is not None
    assert stored is not None
    assert stored.laa_reference == laa_reference
    assert stored.claim_type_id == ClaimType.PAYMENT_ON_ACCOUNT
    assert stored.total_profit_cost_net == Decimal("1000.00")
    assert stored.total_profit_cost_gross == Decimal("1200.00")
    assert stored.total_profit_cost_vat_zero == Decimal("150.00")
    assert stored.poa_type_id == POAType.EXPERT_COST
    assert stored.claimant_id == "claimant-123@provider.co.uk"


def test_create_claim_defaults_status_to_submitted(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = ClaimRepositoryAdapter(session)

    created = adapter.create_claim(str(laa_reference), _make_domain_claim(), None)

    assert created.status_id == ClaimStatus.SUBMITTED


def test_create_claim_sets_submission_date(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = ClaimRepositoryAdapter(session)

    created = adapter.create_claim(str(laa_reference), _make_domain_claim(), None)

    assert created.submission_date is not None


def test_create_claim_persists_optional_fields_as_none_when_omitted(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = ClaimRepositoryAdapter(session)

    created = adapter.create_claim(
        str(laa_reference),
        _make_domain_claim({"claim_type": ClaimType.FINAL_BILL, "poa_type": None}),
        None,
    )

    assert created.poa_type_id is None
    assert created.claimant_id is None


# --- get_claims_by_laa_reference ---


def test_get_claims_by_laa_reference_returns_claims_for_application(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = ClaimRepositoryAdapter(session)
    _create_claim(session, laa_reference)
    _create_claim(session, laa_reference)

    results = adapter.get_claims_by_laa_reference(str(laa_reference))

    assert len(results) == 2
    assert all(c.laa_reference == laa_reference for c in results)


def test_get_claims_by_laa_reference_returns_empty_list_when_no_claims(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = ClaimRepositoryAdapter(session)

    results = adapter.get_claims_by_laa_reference(str(laa_reference))

    assert results == []


# --- create_claim_decision ---


def test_create_claim_decision_persists_decision_with_expected_values(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = ClaimRepositoryAdapter(session)
    claim = _create_claim(session, laa_reference)

    decision = adapter.create_claim_decision(claim.claim_id, ClaimDecisionStatus.REJECT)
    stored = session.get(ClaimDecision, decision.claim_decision_id)

    assert decision.claim_decision_id is not None
    assert stored is not None
    assert stored.claim_id == claim.claim_id
    assert stored.decision == ClaimDecisionStatus.REJECT


# --- create_decision_reason ---


def test_create_decision_reason_persists_reason_with_expected_values(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = ClaimRepositoryAdapter(session)
    claim = _create_claim(session, laa_reference)
    decision = adapter.create_claim_decision(claim.claim_id, ClaimDecisionStatus.REJECT)

    reason = adapter.create_decision_reason(
        decision.claim_decision_id,
        ReasonCode.MAX_POA_CLAIMS_EXCEEDED,
    )
    stored = session.get(DecisionReason, reason.decision_reason_id)

    assert reason.decision_reason_id is not None
    assert stored is not None
    assert stored.claim_decision_id == decision.claim_decision_id
    assert stored.reason_code == ReasonCode.MAX_POA_CLAIMS_EXCEEDED
    assert stored.justification is None


def test_create_decision_reason_persists_justification_when_provided(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = ClaimRepositoryAdapter(session)
    claim = _create_claim(session, laa_reference)
    decision = adapter.create_claim_decision(claim.claim_id, ClaimDecisionStatus.REJECT)

    reason = adapter.create_decision_reason(
        decision.claim_decision_id,
        ReasonCode.MAX_POA_CLAIMS_EXCEEDED,
        justification="Some justification text",
    )

    assert reason.justification == "Some justification text"


# --- update_claim_decision_status ---


def test_update_claim_decision_status_sets_status_on_claim(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = ClaimRepositoryAdapter(session)
    claim = _create_claim(session, laa_reference)
    assert claim.status_id == ClaimStatus.SUBMITTED

    adapter.update_claim_decision_status(claim.claim_id, ClaimStatus.REJECTED)
    session.refresh(claim)

    assert claim.status_id == ClaimStatus.REJECTED


# --- commit / rollback ---


def test_commit_commits_session(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = ClaimRepositoryAdapter(session)
    adapter.create_claim(str(laa_reference), _make_domain_claim(), None)

    adapter.commit()

    stored = session.exec(select(Claim)).all()
    assert len(stored) == 1


def test_rollback_rolls_back_unflushed_changes(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = ClaimRepositoryAdapter(session)
    adapter.create_claim(str(laa_reference), _make_domain_claim(), None)

    adapter.rollback()

    stored = session.exec(select(Claim)).all()
    assert len(stored) == 0
