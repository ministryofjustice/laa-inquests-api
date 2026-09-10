from decimal import Decimal

import pytest

from app.domain.claim_error import ClaimErrorCode, ClaimValidationError
from app.domain.pay_in_full import PayInFullClaim


def test_valid_with_net_and_gross():
    PayInFullClaim(
        profit_cost_net=Decimal("1000.00"),
        profit_cost_gross=Decimal("1200.00"),
    ).validate()


def test_valid_with_vat_zero_only():
    PayInFullClaim(profit_cost_vat_zero=Decimal("500.00")).validate()


def test_valid_with_zero_net_and_gross():
    PayInFullClaim(
        profit_cost_net=Decimal("0.00"),
        profit_cost_gross=Decimal("0.00"),
    ).validate()


def test_valid_with_equal_net_and_gross():
    PayInFullClaim(
        profit_cost_net=Decimal("1200.00"),
        profit_cost_gross=Decimal("1200.00"),
    ).validate()


def test_raises_when_all_totals_missing():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim().validate()

    assert exc.value.code == ClaimErrorCode.MISSING_TOTAL_CLAIM_COST


def test_raises_mixed_vat_when_vat_zero_with_net():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            profit_cost_net=Decimal("1000.00"),
            profit_cost_vat_zero=Decimal("500.00"),
        ).validate()

    assert exc.value.code == ClaimErrorCode.PROFIT_COST_MIXED_VAT


def test_raises_mixed_vat_when_vat_zero_with_gross():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            profit_cost_gross=Decimal("1200.00"),
            profit_cost_vat_zero=Decimal("500.00"),
        ).validate()

    assert exc.value.code == ClaimErrorCode.PROFIT_COST_MIXED_VAT


def test_raises_missing_gross_when_net_only():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(profit_cost_net=Decimal("1000.00")).validate()

    assert exc.value.code == ClaimErrorCode.MISSING_GROSS_TOTAL_WHEN_NET_ENTERED


def test_raises_missing_net_when_gross_only():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(profit_cost_gross=Decimal("1200.00")).validate()

    assert exc.value.code == ClaimErrorCode.MISSING_NET_TOTAL_WHEN_GROSS_ENTERED


def test_raises_when_net_higher_than_gross():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            profit_cost_net=Decimal("1300.00"),
            profit_cost_gross=Decimal("1200.00"),
        ).validate()

    assert exc.value.code == ClaimErrorCode.NET_TOTAL_HIGHER_THAN_GROSS_TOTAL
