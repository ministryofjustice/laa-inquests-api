import uuid
from decimal import Decimal

from sqlmodel import select

from app.adapters.claim_repository_adapter import ClaimRepositoryAdapter
from app.domain.claim import Claim as DomainClaim
from app.models.application.index import Application
from app.models.claim.enums import (
    ClaimStatus,
    ClaimType,
    InquestOutcomeCode,
    NumberOfCounselInstructed,
    POAType,
)
from app.models.claim.index import Claim


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


def test_create_claim_persists_claim_with_expected_values(session):
    application_id = session.exec(select(Application)).first().application_id
    adapter = ClaimRepositoryAdapter(session)

    created_claim = adapter.create_claim(
        application_id,
        _make_domain_claim(
            {
                "poa_type": POAType.EXPERT_COST,
                "vat_zero_total": Decimal("150.00"),
            }
        ),
        "claimant-123@provider.co.uk",
        Decimal("8000.00"),
    )
    stored_claim = session.get(Claim, created_claim.claim_id)

    assert created_claim.claim_id is not None
    assert stored_claim is not None
    assert stored_claim.application_id == application_id
    assert stored_claim.claim_type_id == ClaimType.PAYMENT_ON_ACCOUNT
    assert stored_claim.total_profit_cost_net == Decimal("1000.00")
    assert stored_claim.total_profit_cost_gross == Decimal("1200.00")
    assert stored_claim.total_profit_cost_vat_zero == Decimal("150.00")
    assert stored_claim.total_funds_remaining_after_claim == Decimal("8000.00")


def test_create_claim_defaults_status_to_submitted(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = ClaimRepositoryAdapter(session)

    created_claim = adapter.create_claim(
        str(laa_reference),
        _make_domain_claim(),
        "claimant-123@provider.co.uk",
    )

    assert created_claim.status_id == ClaimStatus.SUBMITTED


def test_create_claim_sets_submission_date(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = ClaimRepositoryAdapter(session)

    created_claim = adapter.create_claim(
        str(laa_reference),
        _make_domain_claim(),
        "claimant-123@provider.co.uk",
    )

    assert created_claim.submission_date is not None


def test_create_claim_persists_optional_poa_type_and_claimant(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = ClaimRepositoryAdapter(session)

    created_claim = adapter.create_claim(
        str(laa_reference),
        _make_domain_claim(),
        "claimant-123@provider.co.uk",
    )

    assert created_claim.poa_type_id == POAType.PROFIT_COST
    assert created_claim.claimant_id == "claimant-123@provider.co.uk"


def test_create_claim_defaults_optional_fields_to_none_when_omitted(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = ClaimRepositoryAdapter(session)

    claim = _make_domain_claim(
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
    )
    created_claim = adapter.create_claim(str(laa_reference), claim, None)

    assert created_claim.poa_type_id is None
    assert created_claim.claimant_id is None


def test_create_claim_persists_final_bill_details(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = ClaimRepositoryAdapter(session)

    claim = _make_domain_claim(
        {
            "claim_type": ClaimType.FINAL_BILL,
            "poa_type": None,
            "net": None,
            "gross": None,
            "vat_zero_total": None,
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
    )
    created_claim = adapter.create_claim(str(laa_reference), claim, None)
    stored_claim = session.get(Claim, created_claim.claim_id)

    assert stored_claim.has_counsel_been_paid is True
    assert stored_claim.has_alternative_funding is False
    assert stored_claim.has_recovery_costs_awarded is True
    assert stored_claim.financial_recovery_previous_pre_certificate_costs == Decimal(
        "100.00"
    )
    assert stored_claim.financial_recovery_cost == Decimal("200.00")
    assert stored_claim.financial_recovery_damages == Decimal("300.00")
    assert stored_claim.financial_recovery_interest == Decimal("50.00")
    assert stored_claim.paying_party == "Test Council"
    assert stored_claim.number_of_counsel_instructed == NumberOfCounselInstructed.TWO


def test_get_claims_by_application_id_returns_all_claims_regardless_of_status(session):
    application_id = session.exec(select(Application)).first().application_id
    adapter = ClaimRepositoryAdapter(session)

    adapter.create_claim(application_id, _make_domain_claim(), None)
    submitted_claim = session.exec(select(Claim)).first()
    submitted_claim.status_id = ClaimStatus.ACCEPTED
    session.add(submitted_claim)
    session.commit()

    adapter.create_claim(application_id, _make_domain_claim(), None)
    adapter.create_claim(application_id, _make_domain_claim(), None)
    all_claims = session.exec(select(Claim)).all()
    all_claims[1].status_id = ClaimStatus.REJECTED
    all_claims[2].status_id = ClaimStatus.REJECTED_WITH_AMENDMENT
    session.commit()

    result = adapter.get_claims_by_application_id(application_id)

    assert len(result) == 3
    returned_statuses = {c.status_id for c in result}
    assert ClaimStatus.ACCEPTED in returned_statuses
    assert ClaimStatus.REJECTED in returned_statuses
    assert ClaimStatus.REJECTED_WITH_AMENDMENT in returned_statuses


def test_get_claims_by_application_id_returns_empty_list_when_no_claims(session):
    application_id = session.exec(select(Application)).first().application_id
    adapter = ClaimRepositoryAdapter(session)

    result = adapter.get_claims_by_application_id(application_id)

    assert result == []
