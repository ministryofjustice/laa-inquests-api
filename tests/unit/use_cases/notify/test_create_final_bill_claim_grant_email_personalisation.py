from datetime import UTC, datetime
from decimal import Decimal

from app.domain.pay_in_full import PayInFullClaim
from app.models.claim.enums import ClaimType
from app.models.claim.index import Claim
from app.models.gov_notify_templates.final_bill_claim_grant_personalisation import (
    NotifyFinalBillClaimGrantTemplatePersonalisation,
)
from app.use_cases.notify.create_final_bill_claim_grant_email_personalisation import (
    create_final_bill_claim_grant_email_personalisation,
)
from tests.unit.factories import create_base_application


def _claim() -> Claim:
    return Claim(
        claim_id=7,
        claim_reference="INQC-0007-0007",
        application_id=12345,
        claim_type_id=ClaimType.FINAL_BILL,
        submission_date=datetime(2026, 6, 18, 14, 3, tzinfo=UTC),
    )


def test_create_final_bill_claim_grant_email_personalisation_returns_expected_data():
    application = create_base_application()
    decision_amounts = PayInFullClaim(
        profit_cost_net=Decimal("1000.00"),
        profit_cost_gross=Decimal("1200.00"),
        disbursement_net=Decimal("100.00"),
        disbursement_gross=Decimal("200.00"),
        disbursement_vat_zero=Decimal("50.00"),
    )

    result = create_final_bill_claim_grant_email_personalisation(
        _claim(),
        application,
        "Test Solicitors",
        decision_amounts,
    )

    assert isinstance(result, NotifyFinalBillClaimGrantTemplatePersonalisation)
    assert result.ref_number == "INQ-YYY-YYY"
    assert result.provider_name == "Test Solicitors"
    assert result.client_first_name == "Jane"
    assert result.client_last_name == "Doe"
    assert result.date_of_claim == "18 June 2026 14:03 UTC"
    assert result.claim_type == "Final bill"
    assert result.claim_ref == "INQC-0007-0007"
    assert result.net_profit_costs == "1,000.00"
    assert result.gross_profit_costs == "1,200.00"
    assert result.zero_vat_profit_costs == "0.00"
    assert result.net_disbursement_costs == "100.00"
    assert result.gross_disbursement_costs == "200.00"
    assert result.zero_vat_disbursement_costs == "50.00"


def test_final_bill_claim_grant_personalisation_totals_gross_profit_and_disbursement():
    decision_amounts = PayInFullClaim(
        profit_cost_net=Decimal("1000.00"),
        profit_cost_gross=Decimal("1200.00"),
        disbursement_net=Decimal("100.00"),
        disbursement_gross=Decimal("200.00"),
    )

    result = create_final_bill_claim_grant_email_personalisation(
        _claim(), create_base_application(), "Firm", decision_amounts
    )

    assert result.claimed_amount == "1,400.00"


def test_final_bill_claim_grant_personalisation_totals_use_vat_zero_when_no_gross():
    decision_amounts = PayInFullClaim(
        profit_cost_vat_zero=Decimal("500.00"),
        disbursement_vat_zero=Decimal("50.00"),
    )

    result = create_final_bill_claim_grant_email_personalisation(
        _claim(), create_base_application(), "Firm", decision_amounts
    )

    assert result.claimed_amount == "550.00"
    assert result.zero_vat_profit_costs == "500.00"
    assert result.gross_profit_costs == "0.00"
