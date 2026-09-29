"""Builders for domain value objects (no ORM, no session)."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.domain.claim import (
    Claim as DomainClaim,  # TODO: Why would we need to alias this? Introduced elsewhere by claims squad. Not sure what the domain represents here
)
from app.domain.claim import ExistingClaimSummary
from app.domain.claim_evidence import ClaimEvidence as DomainClaimEvidence
from app.domain.coroners_letter import CoronersLetter as DomainCoronersLetter
from app.domain.pay_in_full import PayInFullClaim
from app.models.claim.enums import (
    ClaimStatus,
    ClaimType,
    InquestOutcomeCode,
    NumberOfCounselInstructed,
    POAType,
)


def build_domain_claim(**overrides) -> DomainClaim:
    """Payment on account (profit cost) by default."""
    defaults = {
        "claim_type": ClaimType.PAYMENT_ON_ACCOUNT,
        "poa_type": POAType.PROFIT_COST,
        "net": Decimal("1000.00"),
        "gross": Decimal("1200.00"),
        "vat_zero_total": None,
    }
    return DomainClaim(**(defaults | overrides))


def build_final_bill_domain_claim(**overrides) -> DomainClaim:
    defaults = {
        "claim_type": ClaimType.FINAL_BILL,
        "poa_type": None,
        "net": None,
        "gross": Decimal("100.00"),
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
    return DomainClaim(**(defaults | overrides))


def build_nil_bill_domain_claim(**overrides) -> DomainClaim:
    defaults = {
        "claim_type": ClaimType.NIL_BILL,
        "poa_type": None,
        "net": None,
        "gross": Decimal("0.00"),
        "vat_zero_total": None,
        "inquest_outcomes": (InquestOutcomeCode.OPEN_CONCLUSION,),
        "has_alternative_funding": False,
        "has_recovery_costs_awarded": True,
        "financial_recovery_previous_pre_certificate_costs": Decimal("100.00"),
        "financial_recovery_cost": Decimal("200.00"),
        "financial_recovery_damages": Decimal("300.00"),
        "financial_recovery_interest": Decimal("50.00"),
        "paying_party": "Test Council",
    }
    return DomainClaim(**(defaults | overrides))


def build_existing_claim_summary(**overrides) -> ExistingClaimSummary:
    defaults = {
        "claim_type": ClaimType.PAYMENT_ON_ACCOUNT,
        "status": ClaimStatus.SUBMITTED,
        "poa_type": None,
        "submission_date": datetime.now(UTC),
        "net": None,
        "gross": None,
        "vat_zero_total": None,
    }
    return ExistingClaimSummary(**(defaults | overrides))


def build_domain_claim_evidence(**overrides) -> DomainClaimEvidence:
    defaults = {
        "sds_file_name": "claim-evidence_abc123.pdf",
        "file_name": "test-document.pdf",
    }
    return DomainClaimEvidence(**(defaults | overrides))


def build_domain_coroners_letter(**overrides) -> DomainCoronersLetter:
    defaults = {
        "sds_file_name": "coroners-letter_abc123.pdf",
        "file_name": "test-coroners-letter.pdf",
    }
    return DomainCoronersLetter(**(defaults | overrides))


def build_pay_in_full_claim(**overrides) -> PayInFullClaim:
    """Valid profit cost and disbursement totals by default."""
    defaults = {
        "profit_cost_net": Decimal("1000.00"),
        "profit_cost_gross": Decimal("1200.00"),
        "disbursement_net": Decimal("100.00"),
        "disbursement_gross": Decimal("200.00"),
    }
    return PayInFullClaim(**(defaults | overrides))
