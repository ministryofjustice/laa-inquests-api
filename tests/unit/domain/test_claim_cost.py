import pytest

from app.domain.claim_cost import ClaimCost
from app.domain.claim_error import ClaimErrorCode, ClaimValidationError
from app.models.claim.enums import POAType


def test_valid_with_net_and_gross():
    ClaimCost(poa_type=POAType.PROFIT_COST, net=1000, gross=1200, vat_zero_total=None)


def test_valid_with_vat_zero_only():
    ClaimCost(poa_type=POAType.PROFIT_COST, net=None, gross=None, vat_zero_total=500)


def test_valid_when_gross_equals_net():
    ClaimCost(poa_type=POAType.PROFIT_COST, net=1000, gross=1000, vat_zero_total=None)


def test_raises_when_vat_zero_and_net_both_provided():
    with pytest.raises(ClaimValidationError) as exc_info:
        ClaimCost(poa_type=POAType.PROFIT_COST, net=1000, gross=None, vat_zero_total=500)
    assert exc_info.value.code == ClaimErrorCode.PROFIT_COST_MIXED_VAT


def test_raises_when_vat_zero_and_gross_both_provided():
    with pytest.raises(ClaimValidationError) as exc_info:
        ClaimCost(poa_type=POAType.PROFIT_COST, net=None, gross=1200, vat_zero_total=500)
    assert exc_info.value.code == ClaimErrorCode.PROFIT_COST_MIXED_VAT


def test_raises_when_nothing_provided():
    with pytest.raises(ClaimValidationError) as exc_info:
        ClaimCost(poa_type=POAType.PROFIT_COST, net=None, gross=None, vat_zero_total=None)
    assert exc_info.value.code == ClaimErrorCode.MISSING_TOTAL_CLAIM_COST


def test_raises_when_net_provided_without_gross():
    with pytest.raises(ClaimValidationError) as exc_info:
        ClaimCost(poa_type=POAType.PROFIT_COST, net=1000, gross=None, vat_zero_total=None)
    assert exc_info.value.code == ClaimErrorCode.MISSING_GROSS_TOTAL_WHEN_NET_ENTERED


def test_raises_when_net_higher_than_gross():
    with pytest.raises(ClaimValidationError) as exc_info:
        ClaimCost(poa_type=POAType.PROFIT_COST, net=1200, gross=1000, vat_zero_total=None)
    assert exc_info.value.code == ClaimErrorCode.NET_TOTAL_HIGHER_THAN_GROSS_TOTAL


def test_raises_when_net_is_negative():
    with pytest.raises(ClaimValidationError) as exc_info:
        ClaimCost(poa_type=POAType.PROFIT_COST, net=-1, gross=1000, vat_zero_total=None)
    assert exc_info.value.code == ClaimErrorCode.NEGATIVE_NET_COST


def test_no_validation_for_non_profit_cost_poa_type():
    ClaimCost(poa_type=POAType.EXPERT_COST, net=None, gross=None, vat_zero_total=None)


def test_no_validation_when_poa_type_is_none():
    ClaimCost(poa_type=None, net=None, gross=None, vat_zero_total=None)
