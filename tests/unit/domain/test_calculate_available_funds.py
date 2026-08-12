from decimal import Decimal

from app.domain.claim import (
    ApprovedClaimAmount,
    calculate_available_funds,
)
from app.models.claim.enums import ClaimDecisionStatus


def _amount(
    decision: ClaimDecisionStatus | None,
    gross: Decimal | None = None,
    vat_zero_total: Decimal | None = None,
) -> ApprovedClaimAmount:
    return ApprovedClaimAmount(
        decision=decision,
        gross=gross,
        vat_zero_total=vat_zero_total,
    )


def test_returns_full_limit_when_no_claims():
    result = calculate_available_funds(10000, [])

    assert result == Decimal(10000)


def test_subtracts_gross_of_granted_claim():
    claims = [_amount(ClaimDecisionStatus.GRANT, gross=Decimal("1200.00"))]

    result = calculate_available_funds(10000, claims)

    assert result == Decimal("8800.00")


def test_subtracts_gross_of_pay_in_full_claim():
    claims = [_amount(ClaimDecisionStatus.PAY_IN_FULL, gross=Decimal("2500.00"))]

    result = calculate_available_funds(10000, claims)

    assert result == Decimal("7500.00")


def test_uses_vat_zero_when_gross_is_absent():
    claims = [_amount(ClaimDecisionStatus.GRANT, vat_zero_total=Decimal("500.00"))]

    result = calculate_available_funds(10000, claims)

    assert result == Decimal("9500.00")


def test_prefers_gross_over_vat_zero_when_both_present():
    claims = [
        _amount(
            ClaimDecisionStatus.GRANT,
            gross=Decimal("1200.00"),
            vat_zero_total=Decimal("500.00"),
        )
    ]

    result = calculate_available_funds(10000, claims)

    assert result == Decimal("8800.00")


def test_ignores_rejected_claims():
    claims = [_amount(ClaimDecisionStatus.REJECT, gross=Decimal("1200.00"))]

    result = calculate_available_funds(10000, claims)

    assert result == Decimal(10000)


def test_ignores_pending_claims():
    claims = [_amount(ClaimDecisionStatus.PENDING, gross=Decimal("1200.00"))]

    result = calculate_available_funds(10000, claims)

    assert result == Decimal(10000)


def test_ignores_claims_without_a_decision():
    claims = [_amount(None, gross=Decimal("1200.00"))]

    result = calculate_available_funds(10000, claims)

    assert result == Decimal(10000)


def test_sums_only_approved_claims_across_mixed_decisions():
    claims = [
        _amount(ClaimDecisionStatus.GRANT, gross=Decimal("1200.00")),
        _amount(ClaimDecisionStatus.PAY_IN_FULL, vat_zero_total=Decimal("800.00")),
        _amount(ClaimDecisionStatus.REJECT, gross=Decimal("5000.00")),
        _amount(ClaimDecisionStatus.PENDING, gross=Decimal("3000.00")),
        _amount(None, gross=Decimal("999.00")),
    ]

    result = calculate_available_funds(10000, claims)

    assert result == Decimal("8000.00")


def test_can_return_negative_when_approved_claims_exceed_limit():
    claims = [
        _amount(ClaimDecisionStatus.GRANT, gross=Decimal("8000.00")),
        _amount(ClaimDecisionStatus.PAY_IN_FULL, gross=Decimal("4000.00")),
    ]

    result = calculate_available_funds(10000, claims)

    assert result == Decimal("-2000.00")


def test_treats_none_limit_as_zero():
    claims = [_amount(ClaimDecisionStatus.GRANT, gross=Decimal("1200.00"))]

    result = calculate_available_funds(None, claims)

    assert result == Decimal("-1200.00")


def test_treats_approved_claim_with_no_amounts_as_zero():
    claims = [_amount(ClaimDecisionStatus.GRANT)]

    result = calculate_available_funds(10000, claims)

    assert result == Decimal(10000)


def test_accepts_decimal_limit():
    claims = [_amount(ClaimDecisionStatus.GRANT, gross=Decimal("1200.00"))]

    result = calculate_available_funds(Decimal("10000.00"), claims)

    assert result == Decimal("8800.00")


def test_approved_claim_amount_is_approved_flag():
    assert _amount(ClaimDecisionStatus.GRANT).is_approved is True
    assert _amount(ClaimDecisionStatus.PAY_IN_FULL).is_approved is True
    assert _amount(ClaimDecisionStatus.REJECT).is_approved is False
    assert _amount(ClaimDecisionStatus.PENDING).is_approved is False
    assert _amount(None).is_approved is False
