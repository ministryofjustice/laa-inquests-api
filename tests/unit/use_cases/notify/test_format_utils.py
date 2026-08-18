from datetime import UTC, datetime

from app.models.claim.enums import ClaimType
from app.use_cases.notify.format_utils import format_claim_type, format_submitted_at


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
