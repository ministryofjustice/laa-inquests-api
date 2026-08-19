from datetime import UTC, datetime
from decimal import Decimal

from app.models.claim.enums import ClaimType
from app.use_cases.notify.format_utils import (
    format_amount,
    format_claim_type,
    format_submitted_at,
)


def test_format_submitted_at_formats_to_gov_notify_style():
    assert (
        format_submitted_at(datetime(2026, 6, 18, 14, 3, tzinfo=UTC))
        == "18 June 2026 14:03 UTC"
    )


def test_format_claim_type_payment_on_account():
    assert format_claim_type(ClaimType.PAYMENT_ON_ACCOUNT) == "Payment on account"


def test_format_claim_type_final_bill():
    assert format_claim_type(ClaimType.FINAL_BILL) == "Final bill"


def test_format_claim_type_nil_bill():
    assert format_claim_type(ClaimType.NIL_BILL) == "Nil bill"


def test_format_amount_adds_thousands_separator_and_two_decimals():
    assert format_amount(Decimal(1200)) == "1,200.00"


def test_format_amount_pads_to_two_decimal_places():
    assert format_amount(Decimal("500.5")) == "500.50"
