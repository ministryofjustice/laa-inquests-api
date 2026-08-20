from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.models.claim.enums import ClaimType
from app.models.claim.index import Claim
from app.models.gov_notify_templates.claim_reject_personalisation import (
    NotifyClaimRejectTemplatePersonalisation,
)
from app.use_cases.notify.create_claim_rejection_email_personalisation import (
    create_claim_rejection_email_personalisation,
)
from tests.unit.factories import create_base_application

MODULE = "app.use_cases.notify.create_claim_rejection_email_personalisation"


def _claim(**overrides) -> Claim:
    claim = MagicMock(spec=Claim)
    claim.claim_id = 7
    claim.claim_type_id = ClaimType.PAYMENT_ON_ACCOUNT
    claim.submission_date = datetime(2026, 6, 18, 14, 3, tzinfo=UTC)
    claim.total_profit_cost_net = Decimal("1000.00")
    claim.total_profit_cost_gross = Decimal("1200.00")
    claim.total_profit_cost_vat_zero = None
    for key, value in overrides.items():
        setattr(claim, key, value)
    return claim


@patch(f"{MODULE}.datetime")
def test_create_claim_rejection_email_personalisation_returns_expected_data(
    mock_datetime,
):
    mock_datetime.now.return_value = datetime(2026, 8, 18, 9, 30, tzinfo=UTC)
    application = create_base_application()
    claim = _claim()

    result = create_claim_rejection_email_personalisation(
        claim,
        application,
        "Rejected following manual review.",
        "Test Solicitors",
    )

    assert isinstance(result, NotifyClaimRejectTemplatePersonalisation)
    assert result.cert_ref_number == "12345"
    assert result.provider_name == "Test Solicitors"
    assert result.client_first_name == "Jane"
    assert result.client_last_name == "Doe"
    assert result.claim_submitted_at == "18 June 2026 14:03 UTC"
    assert result.claim_type == "Payment on account"
    assert result.total_claim_amount == "1,200.00"
    assert result.date_of_rejection == "18 August 2026 09:30 UTC"
    assert result.justification == "Rejected following manual review."


def test_total_claim_amount_uses_gross_when_no_vat_zero():
    claim = _claim(
        total_profit_cost_net=Decimal("2000.00"),
        total_profit_cost_gross=Decimal("2400.00"),
        total_profit_cost_vat_zero=None,
    )

    result = create_claim_rejection_email_personalisation(
        claim, create_base_application(), "reason", "Firm"
    )

    assert result.total_claim_amount == "2,400.00"


def test_uses_vat_zero_amount_when_vat_zero_present():
    claim = _claim(total_profit_cost_vat_zero=Decimal("500.00"))

    result = create_claim_rejection_email_personalisation(
        claim, create_base_application(), "reason", "Firm"
    )

    assert result.total_claim_amount == "500.00"


def test_raises_when_neither_vat_zero_nor_gross_is_set():
    claim = _claim(total_profit_cost_gross=None, total_profit_cost_vat_zero=None)

    with pytest.raises(ValueError):
        create_claim_rejection_email_personalisation(
            claim, create_base_application(), "reason", "Firm"
        )


def test_claim_type_final_bill_uses_friendly_label():
    claim = _claim(claim_type_id=ClaimType.FINAL_BILL)

    result = create_claim_rejection_email_personalisation(
        claim, create_base_application(), "reason", "Firm"
    )

    assert result.claim_type == "Final bill"


def test_claim_type_nil_bill_uses_friendly_label():
    claim = _claim(claim_type_id=ClaimType.NIL_BILL)

    result = create_claim_rejection_email_personalisation(
        claim, create_base_application(), "reason", "Firm"
    )

    assert result.claim_type == "Nil bill"
