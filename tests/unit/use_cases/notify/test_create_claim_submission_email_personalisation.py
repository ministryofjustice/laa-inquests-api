from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from app.models.claim.enums import ClaimType
from app.models.claim.index import Claim
from app.models.gov_notify_templates.claim_submit_personalisation import (
    NotifyClaimSubmitTemplatePersonalisation,
)
from app.use_cases.notify.create_claim_submission_email_personalisation import (
    create_claim_submission_email_personalisation,
)
from tests.unit.factories import create_base_application


def test_create_claim_submission_email_personalisation_returns_expected_data():
    application = create_base_application()
    claim = MagicMock(spec=Claim)
    claim.submission_date = datetime(2026, 7, 28, 14, 3, tzinfo=UTC)
    claim.claim_reference = "INQC-ABCD-1234"
    claim.claim_type_id = ClaimType.PAYMENT_ON_ACCOUNT
    claim.total_profit_cost_gross = Decimal("1200.00")

    result = create_claim_submission_email_personalisation(
        claim, application, "Test Firm Name"
    )

    assert isinstance(result, NotifyClaimSubmitTemplatePersonalisation)
    assert result.provider_name == "Test Firm Name"
    assert result.ref_number == "INQ-YYY-YYY"
    assert result.client_first_name == "Jane"
    assert result.client_last_name == "Doe"
    assert result.date_of_claim == "28 July 2026 14:03 UTC"
    assert result.claim_type == "Payment on account"
    assert result.claim_reference == "INQC-ABCD-1234"
    assert result.claimed_amount == "1,200.00"


def test_claimed_amount_uses_vat_zero_total_when_gross_is_missing():
    claim = MagicMock(spec=Claim)
    claim.submission_date = datetime(2026, 7, 28, 14, 3, tzinfo=UTC)
    claim.claim_reference = "INQC-ABCD-1234"
    claim.claim_type_id = ClaimType.PAYMENT_ON_ACCOUNT
    claim.total_profit_cost_gross = None
    claim.total_profit_cost_vat_zero = Decimal("500.00")

    result = create_claim_submission_email_personalisation(
        claim, create_base_application(), "Test Firm Name"
    )

    assert result.claimed_amount == "500.00"
