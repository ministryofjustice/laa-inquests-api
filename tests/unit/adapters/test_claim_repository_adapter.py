import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlmodel import select

from app.adapters.claim_repository_adapter import ClaimRepositoryAdapter
from app.domain.claim import Claim as DomainClaim
from app.models.application.index import Application
from app.models.claim.enums import (
    ClaimDecisionStatus,
    ClaimStatus,
    ClaimType,
    InquestOutcomeCode,
    NumberOfCounselInstructed,
    POAType,
    ReasonCode,
)
from app.models.claim.index import (
    Claim,
    ClaimCostTemplate,
    ClaimDecision,
    ClaimEvidence,
    ClaimInquestOutcome,
    DecisionReason,
)


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
        _make_domain_claim(
            {
                "claim_type": ClaimType.FINAL_BILL,
                "poa_type": None,
                "inquest_outcomes": (InquestOutcomeCode.NATURAL_CAUSES,),
                "cost_template_file_id": uuid.uuid4(),
                "cost_template_file_name": "costs.xlsx",
                "has_counsel_been_paid": True,
                "has_alternative_funding": False,
                "has_recovery_costs_awarded": True,
                "financial_recovery_previous_pre_certificate_costs": Decimal("100.00"),
                "financial_recovery_cost": Decimal("200.00"),
                "financial_recovery_damages": Decimal("300.00"),
                "financial_recovery_interest": Decimal("50.00"),
                "paying_party": "Test Council",
                "number_of_counsel_instructed": NumberOfCounselInstructed.TWO,
            }
        ),
        None,
    )

    assert created.poa_type_id is None
    assert created.claimant_id is None


def test_link_inquest_outcomes_to_claim_persists_link_rows(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = ClaimRepositoryAdapter(session)
    created = adapter.create_claim(
        str(laa_reference),
        _make_domain_claim(
            {
                "claim_type": ClaimType.FINAL_BILL,
                "poa_type": None,
                "inquest_outcomes": (InquestOutcomeCode.NATURAL_CAUSES,),
                "cost_template_file_id": uuid.uuid4(),
                "cost_template_file_name": "costs.xlsx",
                "has_counsel_been_paid": True,
                "has_alternative_funding": False,
                "has_recovery_costs_awarded": True,
                "financial_recovery_previous_pre_certificate_costs": Decimal("100.00"),
                "financial_recovery_cost": Decimal("200.00"),
                "financial_recovery_damages": Decimal("300.00"),
                "financial_recovery_interest": Decimal("50.00"),
                "paying_party": "Test Council",
                "number_of_counsel_instructed": NumberOfCounselInstructed.TWO,
            }
        ),
        None,
    )

    adapter.link_inquest_outcomes_to_claim(
        created.claim_id,
        [InquestOutcomeCode.NARRATIVE_CONCLUSION, InquestOutcomeCode.NATURAL_CAUSES],
    )
    adapter.commit()

    stored = session.exec(
        select(ClaimInquestOutcome).where(
            ClaimInquestOutcome.claim_id == created.claim_id
        )
    ).all()
    assert {row.inquest_outcome_id for row in stored} == {
        InquestOutcomeCode.NARRATIVE_CONCLUSION,
        InquestOutcomeCode.NATURAL_CAUSES,
    }


def test_link_cost_template_to_claim_persists_row(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = ClaimRepositoryAdapter(session)
    created = adapter.create_claim(
        str(laa_reference),
        _make_domain_claim(
            {
                "claim_type": ClaimType.FINAL_BILL,
                "poa_type": None,
                "inquest_outcomes": (InquestOutcomeCode.NATURAL_CAUSES,),
                "cost_template_file_id": uuid.uuid4(),
                "cost_template_file_name": "costs.xlsx",
                "has_counsel_been_paid": True,
                "has_alternative_funding": False,
                "has_recovery_costs_awarded": True,
                "financial_recovery_previous_pre_certificate_costs": Decimal("100.00"),
                "financial_recovery_cost": Decimal("200.00"),
                "financial_recovery_damages": Decimal("300.00"),
                "financial_recovery_interest": Decimal("50.00"),
                "paying_party": "Test Council",
                "number_of_counsel_instructed": NumberOfCounselInstructed.TWO,
            }
        ),
        None,
    )
    file_id = uuid.uuid4()

    adapter.link_cost_template_to_claim(
        created.claim_id, file_id, "final_bill_costs.xlsx"
    )
    adapter.commit()

    stored = session.exec(
        select(ClaimCostTemplate).where(ClaimCostTemplate.claim_id == created.claim_id)
    ).all()
    assert len(stored) == 1
    assert stored[0].claim_cost_template_file_id == file_id
    assert stored[0].claim_cost_template_file_name == "final_bill_costs.xlsx"


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


def test_get_open_claims_returns_only_open_claims(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = ClaimRepositoryAdapter(session)

    open_claim = _create_claim(session, laa_reference)
    rejected_claim = _create_claim(session, laa_reference)
    rejected_claim.status_id = ClaimStatus.REJECTED
    session.add(rejected_claim)
    session.commit()

    results = adapter.get_open_claims()

    assert len(results) == 1
    assert results[0].claim_id == open_claim.claim_id
    assert all(claim.status_id == ClaimStatus.SUBMITTED for claim in results)


def test_get_open_claims_returned_claims_have_matching_application(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    _create_claim(session, laa_reference)

    adapter = ClaimRepositoryAdapter(session)
    results = adapter.get_open_claims()

    for claim in results:
        assert claim.application.laa_reference == claim.laa_reference


def test_get_open_claims_orders_by_submission_date_ascending(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = ClaimRepositoryAdapter(session)

    newer_claim = _create_claim(session, laa_reference)
    older_claim = _create_claim(session, laa_reference)

    newer_claim.submission_date = datetime(2026, 6, 1, tzinfo=UTC)
    older_claim.submission_date = datetime(2026, 1, 1, tzinfo=UTC)

    session.add(newer_claim)
    session.add(older_claim)
    session.commit()

    results = adapter.get_open_claims()

    assert len(results) == 2
    assert results[0].claim_id == older_claim.claim_id
    assert results[1].claim_id == newer_claim.claim_id


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


def test_link_evidence_to_claim_sets_claim_id_on_existing_evidence(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = ClaimRepositoryAdapter(session)
    claim = _create_claim(session, laa_reference)
    evidence = ClaimEvidence(sds_file_name="stored.pdf", file_name="original.pdf")
    session.add(evidence)
    session.commit()
    session.refresh(evidence)

    adapter.link_evidence_to_claim(claim.claim_id, [evidence.claim_evidence_id])

    stored = session.get(ClaimEvidence, evidence.claim_evidence_id)
    assert stored.claim_id == claim.claim_id


def test_link_evidence_to_claim_ignores_unknown_evidence_ids(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = ClaimRepositoryAdapter(session)
    claim = _create_claim(session, laa_reference)

    adapter.link_evidence_to_claim(claim.claim_id, [uuid.uuid4()])  # should not raise


def test_delete_claim_evidence_by_id_deletes_existing_evidence(session):
    adapter = ClaimRepositoryAdapter(session)
    evidence = ClaimEvidence(sds_file_name="stored.pdf", file_name="original.pdf")
    session.add(evidence)
    session.commit()
    session.refresh(evidence)

    deleted = adapter.delete_claim_evidence_by_id(evidence.claim_evidence_id)

    assert deleted is True
    assert session.get(ClaimEvidence, evidence.claim_evidence_id) is None


def test_delete_claim_evidence_by_id_returns_false_for_unknown_id(session):
    adapter = ClaimRepositoryAdapter(session)

    deleted = adapter.delete_claim_evidence_by_id(uuid.uuid4())

    assert deleted is False


def test_update_claim_status_sets_status_on_claim(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = ClaimRepositoryAdapter(session)
    claim = _create_claim(session, laa_reference)
    assert claim.status_id == ClaimStatus.SUBMITTED

    adapter.update_claim_status(claim.claim_id, ClaimStatus.REJECTED)
    session.refresh(claim)

    assert claim.status_id == ClaimStatus.REJECTED


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
