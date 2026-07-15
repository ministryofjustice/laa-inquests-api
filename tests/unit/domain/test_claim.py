from decimal import Decimal

import pytest

from app.domain.claim import Claim
from app.domain.claim_error import ClaimErrorCode, ClaimValidationError
from app.models.claim.enums import ClaimType, POAType


def test_valid_with_net_and_gross():
    Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.PROFIT_COST,
        net=1000,
        gross=1200,
        vat_zero_total=None,
    )


def test_valid_with_vat_zero_only():
    Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.PROFIT_COST,
        net=None,
        gross=None,
        vat_zero_total=500,
    )


def test_valid_when_gross_equals_net():
    Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.PROFIT_COST,
        net=1000,
        gross=1000,
        vat_zero_total=None,
    )


def test_raises_when_vat_zero_and_net_both_provided():
    with pytest.raises(ClaimValidationError) as exc_info:
        Claim(
            claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
            poa_type=POAType.PROFIT_COST,
            net=1000,
            gross=None,
            vat_zero_total=500,
        )
    assert exc_info.value.code == ClaimErrorCode.PROFIT_COST_MIXED_VAT


def test_raises_when_vat_zero_and_gross_both_provided():
    with pytest.raises(ClaimValidationError) as exc_info:
        Claim(
            claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
            poa_type=POAType.PROFIT_COST,
            net=None,
            gross=1200,
            vat_zero_total=500,
        )
    assert exc_info.value.code == ClaimErrorCode.PROFIT_COST_MIXED_VAT


def test_raises_when_nothing_provided():
    with pytest.raises(ClaimValidationError) as exc_info:
        Claim(
            claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
            poa_type=POAType.PROFIT_COST,
            net=None,
            gross=None,
            vat_zero_total=None,
        )
    assert exc_info.value.code == ClaimErrorCode.MISSING_TOTAL_CLAIM_COST


def test_raises_when_net_provided_without_gross():
    with pytest.raises(ClaimValidationError) as exc_info:
        Claim(
            claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
            poa_type=POAType.PROFIT_COST,
            net=1000,
            gross=None,
            vat_zero_total=None,
        )
    assert exc_info.value.code == ClaimErrorCode.MISSING_GROSS_TOTAL_WHEN_NET_ENTERED


def test_raises_when_net_higher_than_gross():
    with pytest.raises(ClaimValidationError) as exc_info:
        Claim(
            claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
            poa_type=POAType.PROFIT_COST,
            net=1200,
            gross=1000,
            vat_zero_total=None,
        )
    assert exc_info.value.code == ClaimErrorCode.NET_TOTAL_HIGHER_THAN_GROSS_TOTAL


def test_raises_when_net_is_negative():
    with pytest.raises(ClaimValidationError) as exc_info:
        Claim(
            claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
            poa_type=POAType.PROFIT_COST,
            net=-1,
            gross=1000,
            vat_zero_total=None,
        )
    assert exc_info.value.code == ClaimErrorCode.NEGATIVE_NET_COST


def test_raises_when_non_profit_cost_has_no_totals():
    with pytest.raises(ClaimValidationError) as exc_info:
        Claim(
            claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
            poa_type=POAType.EXPERT_COST,
            net=None,
            gross=None,
            vat_zero_total=None,
        )

    assert exc_info.value.code == ClaimErrorCode.MISSING_NON_PROFIT_COST_TOTAL


def test_non_profit_cost_defaults_missing_totals_to_zero():
    claim = Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.EXPERT_COST,
        net=None,
        gross=None,
        vat_zero_total=Decimal("150.00"),
    )

    assert claim.net == Decimal("0.00")
    assert claim.gross == Decimal("0.00")
    assert claim.vat_zero_total == Decimal("150.00")


def test_raises_when_non_profit_cost_net_higher_than_gross():
    with pytest.raises(ClaimValidationError) as exc_info:
        Claim(
            claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
            poa_type=POAType.NON_EXPERT_DISBURSEMENT,
            net=Decimal("120.00"),
            gross=Decimal("100.00"),
            vat_zero_total=None,
        )

    assert exc_info.value.code == ClaimErrorCode.NET_TOTAL_HIGHER_THAN_GROSS_TOTAL


def test_no_validation_when_poa_type_is_none():
    Claim(
        claim_type=ClaimType.FINAL_BILL,
        poa_type=None,
        net=None,
        gross=None,
        vat_zero_total=None,
    )


def test_raises_when_payment_on_account_without_poa_type():
    with pytest.raises(ClaimValidationError) as exc_info:
        Claim(
            claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
            poa_type=None,
            net=None,
            gross=None,
            vat_zero_total=None,
        )
    assert exc_info.value.code == ClaimErrorCode.MISSING_POA_TYPE_FOR_PAYMENT_ON_ACCOUNT


def test_raises_when_non_payment_on_account_with_poa_type():
    with pytest.raises(ClaimValidationError) as exc_info:
        Claim(
            claim_type=ClaimType.FINAL_BILL,
            poa_type=POAType.PROFIT_COST,
            net=None,
            gross=None,
            vat_zero_total=None,
        )
    assert (
        exc_info.value.code
        == ClaimErrorCode.POA_TYPE_NOT_ALLOWED_FOR_NON_PAYMENT_ON_ACCOUNT
    )
