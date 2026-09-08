from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.models.claim.enums import ClaimType
from app.models.claim.index import Claim
from app.models.gov_notify_templates.final_bill_claim_reject_personalisation import (
    NotifyFinalBillClaimRejectTemplatePersonalisation,
)
from app.use_cases.notify.create_final_bill_claim_rejection_email_personalisation import (
    create_final_bill_claim_rejection_email_personalisation,
)
from tests.unit.factories import create_base_application

MODULE = "app.use_cases.notify.create_final_bill_claim_rejection_email_personalisation"


def test_create_final_bill_claim_rejection_email_personalisation_returns_expected_data():
    application = create_base_application()
    claim = Claim(
        claim_id=7,
        application_id=12345,
        claim_type_id=ClaimType.FINAL_BILL,
        submission_date=datetime(2026, 6, 18, 14, 3, tzinfo=UTC),
        total_profit_cost_gross=Decimal("1200.00"),
    )

    with patch(f"{MODULE}.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2026, 8, 18, 9, 30, tzinfo=UTC)
        result = create_final_bill_claim_rejection_email_personalisation(
            claim,
            application,
            "Rejected following manual review.",
            "Test Solicitors",
        )

    assert isinstance(result, NotifyFinalBillClaimRejectTemplatePersonalisation)
    assert result.ref_number == "INQ-YYY-YYY"
    assert result.provider_name == "Test Solicitors"
    assert result.client_first_name == "Jane"
    assert result.client_last_name == "Doe"
    assert result.date_of_claim == "18 June 2026 14:03 UTC"
    assert result.claim_type == "Final bill"
    assert result.claim_ref == "7"
    assert result.claimed_amount == "1,200.00"
    assert result.reason_for_refusal == "Rejected following manual review."
    assert result.date_of_rejection == "18 August 2026 09:30 UTC"


def test_final_bill_claim_rejection_personalisation_uses_vat_zero_amount():
    claim = MagicMock(spec=Claim)
    claim.claim_id = 7
    claim.claim_type_id = ClaimType.FINAL_BILL
    claim.submission_date = datetime(2026, 6, 18, 14, 3, tzinfo=UTC)
    claim.total_profit_cost_vat_zero = Decimal("500.00")
    claim.total_profit_cost_gross = Decimal("1200.00")

    result = create_final_bill_claim_rejection_email_personalisation(
        claim, create_base_application(), "reason", "Firm"
    )

    assert result.claimed_amount == "500.00"
