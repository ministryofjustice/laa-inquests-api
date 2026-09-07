from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.models.claim.enums import ClaimType
from app.models.claim.index import Claim
from app.models.gov_notify_templates.claim_grant_personalisation import (
    NotifyClaimGrantTemplatePersonalisation,
)
from app.use_cases.notify.create_claim_grant_email_personalisation import (
    create_claim_grant_email_personalisation,
)
from tests.unit.factories import create_base_application


def _claim(**overrides) -> Claim:
    claim = MagicMock(spec=Claim)
    claim.claim_id = 7
    claim.claim_type_id = ClaimType.PAYMENT_ON_ACCOUNT
    claim.submission_date = datetime(2026, 6, 18, 14, 3, tzinfo=UTC)
    claim.total_profit_cost_net = Decimal("1000.00")
    claim.total_profit_cost_gross = Decimal("1200.00")
    claim.total_profit_cost_vat_zero = Decimal("1150.00")
    for key, value in overrides.items():
        setattr(claim, key, value)
    return claim


def test_create_claim_grant_email_personalisation_returns_expected_data():
    application = create_base_application()
    claim = _claim()

    result = create_claim_grant_email_personalisation(
        claim, application, "Test Solicitors"
    )

    assert isinstance(result, NotifyClaimGrantTemplatePersonalisation)
    assert result.ref_number == "12345"
    assert result.provider_name == "Test Solicitors"
    assert result.client_first_name == "Jane"
    assert result.client_last_name == "Doe"
    assert result.date_of_claim == "18 June 2026 14:03 UTC"
    assert result.claim_type == "Payment on account"
    assert result.claim_ref == "7"
    assert result.zero_vat_POA_costs == "1,150.00"
    assert result.net_POA_costs == "1,000.00"
    assert result.gross_POA_costs == "1,200.00"


def test_missing_costs_default_to_zero():
    claim = _claim(
        total_profit_cost_vat_zero=None,
        total_profit_cost_net=None,
        total_profit_cost_gross=None,
    )

    result = create_claim_grant_email_personalisation(
        claim, create_base_application(), "Firm"
    )

    assert result.zero_vat_POA_costs == "0.00"
    assert result.net_POA_costs == "0.00"
    assert result.gross_POA_costs == "0.00"


def test_claim_type_final_bill_uses_friendly_label():
    claim = _claim(claim_type_id=ClaimType.FINAL_BILL)

    result = create_claim_grant_email_personalisation(
        claim, create_base_application(), "Firm"
    )

    assert result.claim_type == "Final bill"


def test_claim_type_nil_bill_uses_friendly_label():
    claim = _claim(claim_type_id=ClaimType.NIL_BILL)

    result = create_claim_grant_email_personalisation(
        claim, create_base_application(), "Firm"
    )

    assert result.claim_type == "Nil bill"


def test_model_rejects_missing_required_fields():
    with pytest.raises(ValidationError):
        NotifyClaimGrantTemplatePersonalisation(ref_number="12345")


def test_model_rejects_extra_fields():
    with pytest.raises(ValidationError):
        NotifyClaimGrantTemplatePersonalisation(
            ref_number="12345",
            provider_name="Firm",
            client_first_name="Jane",
            client_last_name="Doe",
            date_of_claim="18 June 2026 14:03 UTC",
            claim_type="Payment on account",
            claim_ref="7",
            zero_vat_POA_costs="0.00",
            net_POA_costs="0.00",
            gross_POA_costs="0.00",
            unexpected_field="not allowed",
        )
