from decimal import Decimal

import pytest

from app.domain.claim_error import ClaimErrorCode, ClaimValidationError
from app.domain.pay_in_full import PayInFullClaim

VALID_PROFIT_COST = {
    "profit_cost_net": Decimal("1000.00"),
    "profit_cost_gross": Decimal("1200.00"),
}
VALID_DISBURSEMENT = {
    "disbursement_net": Decimal("100.00"),
    "disbursement_gross": Decimal("200.00"),
}


# Profit cost group


def test_valid_with_net_and_gross():
    PayInFullClaim(
        profit_cost_net=Decimal("1000.00"),
        profit_cost_gross=Decimal("1200.00"),
        **VALID_DISBURSEMENT,
    ).validate()


def test_valid_with_vat_zero_only():
    PayInFullClaim(
        profit_cost_vat_zero=Decimal("500.00"),
        **VALID_DISBURSEMENT,
    ).validate()


def test_valid_with_zero_net_and_gross():
    PayInFullClaim(
        profit_cost_net=Decimal("0.00"),
        profit_cost_gross=Decimal("0.00"),
        **VALID_DISBURSEMENT,
    ).validate()


def test_valid_with_equal_net_and_gross():
    PayInFullClaim(
        profit_cost_net=Decimal("1200.00"),
        profit_cost_gross=Decimal("1200.00"),
        **VALID_DISBURSEMENT,
    ).validate()


def test_raises_when_all_totals_missing():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(**VALID_DISBURSEMENT).validate()

    assert exc.value.code == ClaimErrorCode.MISSING_TOTAL_CLAIM_COST


def test_raises_mixed_vat_when_vat_zero_with_net():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            profit_cost_net=Decimal("1000.00"),
            profit_cost_vat_zero=Decimal("500.00"),
            **VALID_DISBURSEMENT,
        ).validate()

    assert exc.value.code == ClaimErrorCode.PROFIT_COST_MIXED_VAT


def test_raises_mixed_vat_when_vat_zero_with_gross():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            profit_cost_gross=Decimal("1200.00"),
            profit_cost_vat_zero=Decimal("500.00"),
            **VALID_DISBURSEMENT,
        ).validate()

    assert exc.value.code == ClaimErrorCode.PROFIT_COST_MIXED_VAT


def test_raises_missing_gross_when_net_only():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            profit_cost_net=Decimal("1000.00"),
            **VALID_DISBURSEMENT,
        ).validate()

    assert exc.value.code == ClaimErrorCode.MISSING_GROSS_TOTAL_WHEN_NET_ENTERED


def test_raises_missing_net_when_gross_only():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            profit_cost_gross=Decimal("1200.00"),
            **VALID_DISBURSEMENT,
        ).validate()

    assert exc.value.code == ClaimErrorCode.MISSING_NET_TOTAL_WHEN_GROSS_ENTERED


def test_raises_when_net_higher_than_gross():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            profit_cost_net=Decimal("1300.00"),
            profit_cost_gross=Decimal("1200.00"),
            **VALID_DISBURSEMENT,
        ).validate()

    assert exc.value.code == ClaimErrorCode.NET_TOTAL_HIGHER_THAN_GROSS_TOTAL


# Disbursement group


def test_valid_disbursement_with_net_and_gross():
    PayInFullClaim(
        **VALID_PROFIT_COST,
        disbursement_net=Decimal("100.00"),
        disbursement_gross=Decimal("120.00"),
    ).validate()


def test_valid_disbursement_with_vat_zero_only():
    PayInFullClaim(
        **VALID_PROFIT_COST,
        disbursement_vat_zero=Decimal("50.00"),
    ).validate()


def test_valid_disbursement_with_vat_zero_net_and_gross():
    PayInFullClaim(
        **VALID_PROFIT_COST,
        disbursement_net=Decimal("100.00"),
        disbursement_gross=Decimal("200.00"),
        disbursement_vat_zero=Decimal("50.00"),
    ).validate()


def test_valid_disbursement_with_zero_net():
    PayInFullClaim(
        **VALID_PROFIT_COST,
        disbursement_net=Decimal("0.00"),
        disbursement_gross=Decimal("120.00"),
    ).validate()


def test_raises_when_disbursement_totals_missing():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(**VALID_PROFIT_COST).validate()

    assert exc.value.code == ClaimErrorCode.MISSING_DISBURSEMENT_TOTAL


def test_raises_missing_disbursement_gross_when_net_only():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            **VALID_PROFIT_COST,
            disbursement_net=Decimal("100.00"),
        ).validate()

    assert exc.value.code == ClaimErrorCode.MISSING_DISBURSEMENT_GROSS_WHEN_NET_ENTERED


def test_raises_missing_disbursement_net_when_gross_only():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            **VALID_PROFIT_COST,
            disbursement_gross=Decimal("120.00"),
        ).validate()

    assert exc.value.code == ClaimErrorCode.MISSING_DISBURSEMENT_NET_WHEN_GROSS_ENTERED


def test_raises_when_disbursement_gross_not_greater_than_net():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            **VALID_PROFIT_COST,
            disbursement_net=Decimal("120.00"),
            disbursement_gross=Decimal("120.00"),
        ).validate()

    assert exc.value.code == ClaimErrorCode.DISBURSEMENT_GROSS_NOT_GREATER_THAN_TOTAL


def test_raises_when_disbursement_gross_not_greater_than_vat_zero_plus_net():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            **VALID_PROFIT_COST,
            disbursement_net=Decimal("100.00"),
            disbursement_gross=Decimal("120.00"),
            disbursement_vat_zero=Decimal("50.00"),
        ).validate()

    assert exc.value.code == ClaimErrorCode.DISBURSEMENT_GROSS_NOT_GREATER_THAN_TOTAL


def test_valid_with_all_zero_disbursement_totals():
    PayInFullClaim(
        **VALID_PROFIT_COST,
        disbursement_net=Decimal("0.00"),
        disbursement_gross=Decimal("0.00"),
        disbursement_vat_zero=Decimal("0.00"),
    ).validate()


def test_valid_with_zero_net_and_gross_and_vat_zero_amount():
    PayInFullClaim(
        **VALID_PROFIT_COST,
        disbursement_net=Decimal("0.00"),
        disbursement_gross=Decimal("0.00"),
        disbursement_vat_zero=Decimal("50.00"),
    ).validate()


def test_valid_with_zero_net_and_gross_and_no_vat_zero():
    PayInFullClaim(
        **VALID_PROFIT_COST,
        disbursement_net=Decimal("0.00"),
        disbursement_gross=Decimal("0.00"),
    ).validate()


def test_profit_cost_error_takes_priority_over_disbursement_error():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim().validate()

    assert exc.value.code == ClaimErrorCode.MISSING_TOTAL_CLAIM_COST

ZERO = Decimal("0.00")


@pytest.mark.parametrize(
    "amounts",
    [
        pytest.param(
            {
                "profit_cost_net": ZERO,
                "profit_cost_gross": ZERO,
                "disbursement_net": ZERO,
                "disbursement_gross": ZERO,
            },
            id="standard_rated_fields_zero",
        ),
        pytest.param(
            {"profit_cost_vat_zero": ZERO, "disbursement_vat_zero": ZERO},
            id="vat_zero_fields_zero",
        ),
        pytest.param(
            {
                "profit_cost_net": ZERO,
                "profit_cost_gross": ZERO,
                "disbursement_net": ZERO,
                "disbursement_gross": ZERO,
                "disbursement_vat_zero": ZERO,
            },
            id="all_disbursement_fields_zero",
        ),
    ],
)
def test_is_nil_bill_when_all_approved_amounts_are_zero(amounts):
    assert PayInFullClaim(**amounts).is_nil_bill is True


@pytest.mark.parametrize(
    "amounts",
    [
        pytest.param(
            {**VALID_PROFIT_COST, "disbursement_vat_zero": ZERO},
            id="profit_cost_gross_set",
        ),
        pytest.param(
            {
                "profit_cost_net": ZERO,
                "profit_cost_gross": ZERO,
                "disbursement_net": ZERO,
                "disbursement_gross": ZERO,
                "disbursement_vat_zero": Decimal("50.00"),
            },
            id="disbursement_vat_zero_set",
        ),
        pytest.param(
            {
                "profit_cost_vat_zero": Decimal("-5.00"),
                "disbursement_vat_zero": ZERO,
            },
            id="negative_amount",
        ),
    ],
)
def test_is_not_nil_bill_when_any_approved_amount_is_non_zero(amounts):
    assert PayInFullClaim(**amounts).is_nil_bill is False
