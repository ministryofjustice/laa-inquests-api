from decimal import Decimal

import pytest

from app.domain.claim_error import ClaimErrorCode, ClaimValidationError
from app.domain.pay_in_full import (
    PayInFullClaim,
    pay_in_full_claim_from_submitted_poa_claim,
)
from app.models.claim.enums import ClaimType, POAType
from app.models.claim.index import Claim

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
        claim_type_id=ClaimType.FINAL_BILL,
        profit_cost_net=Decimal("1000.00"),
        profit_cost_gross=Decimal("1200.00"),
        **VALID_DISBURSEMENT,
    ).validate()


def test_valid_with_vat_zero_only():
    PayInFullClaim(
        claim_type_id=ClaimType.FINAL_BILL,
        profit_cost_vat_zero=Decimal("500.00"),
        **VALID_DISBURSEMENT,
    ).validate()


def test_valid_with_zero_net_and_gross():
    PayInFullClaim(
        claim_type_id=ClaimType.FINAL_BILL,
        profit_cost_net=Decimal("0.00"),
        profit_cost_gross=Decimal("0.00"),
        **VALID_DISBURSEMENT,
    ).validate()


def test_valid_with_equal_net_and_gross():
    PayInFullClaim(
        claim_type_id=ClaimType.FINAL_BILL,
        profit_cost_net=Decimal("1200.00"),
        profit_cost_gross=Decimal("1200.00"),
        **VALID_DISBURSEMENT,
    ).validate()


def test_raises_when_all_totals_missing():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            claim_type_id=ClaimType.FINAL_BILL, **VALID_DISBURSEMENT
        ).validate()

    assert exc.value.code == ClaimErrorCode.MISSING_TOTAL_CLAIM_COST


def test_raises_mixed_vat_when_vat_zero_with_net():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            claim_type_id=ClaimType.FINAL_BILL,
            profit_cost_net=Decimal("1000.00"),
            profit_cost_vat_zero=Decimal("500.00"),
            **VALID_DISBURSEMENT,
        ).validate()

    assert exc.value.code == ClaimErrorCode.PROFIT_COST_MIXED_VAT


def test_raises_mixed_vat_when_vat_zero_with_gross():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            claim_type_id=ClaimType.FINAL_BILL,
            profit_cost_gross=Decimal("1200.00"),
            profit_cost_vat_zero=Decimal("500.00"),
            **VALID_DISBURSEMENT,
        ).validate()

    assert exc.value.code == ClaimErrorCode.PROFIT_COST_MIXED_VAT


def test_raises_missing_gross_when_net_only():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            claim_type_id=ClaimType.FINAL_BILL,
            profit_cost_net=Decimal("1000.00"),
            **VALID_DISBURSEMENT,
        ).validate()

    assert exc.value.code == ClaimErrorCode.MISSING_GROSS_TOTAL_WHEN_NET_ENTERED


def test_raises_missing_net_when_gross_only():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            claim_type_id=ClaimType.FINAL_BILL,
            profit_cost_gross=Decimal("1200.00"),
            **VALID_DISBURSEMENT,
        ).validate()

    assert exc.value.code == ClaimErrorCode.MISSING_NET_TOTAL_WHEN_GROSS_ENTERED


def test_raises_when_net_higher_than_gross():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            claim_type_id=ClaimType.FINAL_BILL,
            profit_cost_net=Decimal("1300.00"),
            profit_cost_gross=Decimal("1200.00"),
            **VALID_DISBURSEMENT,
        ).validate()

    assert exc.value.code == ClaimErrorCode.NET_TOTAL_HIGHER_THAN_GROSS_TOTAL


# Nil bill claim type


def test_valid_nil_bill_claim_with_no_amounts_at_all():
    PayInFullClaim(claim_type_id=ClaimType.NIL_BILL).validate()


def test_raises_when_profit_cost_amounts_supplied_for_nil_bill_claim():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            claim_type_id=ClaimType.NIL_BILL,
            profit_cost_net=Decimal("0.00"),
            profit_cost_gross=Decimal("0.00"),
        ).validate()

    assert exc.value.code == ClaimErrorCode.PROFIT_COST_NOT_ALLOWED_FOR_NIL_BILL_CLAIM


def test_raises_when_disbursement_amounts_supplied_for_nil_bill_claim():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            claim_type_id=ClaimType.NIL_BILL,
            disbursement_net=Decimal("0.00"),
            disbursement_gross=Decimal("0.00"),
        ).validate()

    assert exc.value.code == ClaimErrorCode.DISBURSEMENT_NOT_ALLOWED_FOR_NIL_BILL_CLAIM


@pytest.mark.parametrize(
    "claim_type",
    [ClaimType.FINAL_BILL, ClaimType.PAYMENT_ON_ACCOUNT],
)
def test_raises_when_all_totals_missing_for_non_nil_bill_claim_types(claim_type):
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(claim_type_id=claim_type).validate()

    assert exc.value.code == ClaimErrorCode.MISSING_TOTAL_CLAIM_COST


def test_raises_profit_cost_not_allowed_for_nil_bill_even_with_mixed_vat_shape():
    """A nil bill's profit-cost check takes priority over the general mixed-VAT
    rule, since no profit cost amounts are allowed at all for a nil bill."""
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            claim_type_id=ClaimType.NIL_BILL,
            profit_cost_net=Decimal("1000.00"),
            profit_cost_vat_zero=Decimal("500.00"),
            **VALID_DISBURSEMENT,
        ).validate()

    assert exc.value.code == ClaimErrorCode.PROFIT_COST_NOT_ALLOWED_FOR_NIL_BILL_CLAIM


# Disbursement group


def test_valid_disbursement_with_net_and_gross():
    PayInFullClaim(
        claim_type_id=ClaimType.FINAL_BILL,
        **VALID_PROFIT_COST,
        disbursement_net=Decimal("100.00"),
        disbursement_gross=Decimal("120.00"),
    ).validate()


def test_valid_disbursement_with_vat_zero_only():
    PayInFullClaim(
        claim_type_id=ClaimType.FINAL_BILL,
        **VALID_PROFIT_COST,
        disbursement_vat_zero=Decimal("50.00"),
    ).validate()


def test_valid_disbursement_with_vat_zero_net_and_gross():
    PayInFullClaim(
        claim_type_id=ClaimType.FINAL_BILL,
        **VALID_PROFIT_COST,
        disbursement_net=Decimal("100.00"),
        disbursement_gross=Decimal("200.00"),
        disbursement_vat_zero=Decimal("50.00"),
    ).validate()


def test_valid_disbursement_with_zero_net():
    PayInFullClaim(
        claim_type_id=ClaimType.FINAL_BILL,
        **VALID_PROFIT_COST,
        disbursement_net=Decimal("0.00"),
        disbursement_gross=Decimal("120.00"),
    ).validate()


def test_raises_when_disbursement_totals_missing():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            claim_type_id=ClaimType.FINAL_BILL, **VALID_PROFIT_COST
        ).validate()

    assert exc.value.code == ClaimErrorCode.MISSING_DISBURSEMENT_TOTAL


def test_raises_missing_disbursement_gross_when_net_only():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            claim_type_id=ClaimType.FINAL_BILL,
            **VALID_PROFIT_COST,
            disbursement_net=Decimal("100.00"),
        ).validate()

    assert exc.value.code == ClaimErrorCode.MISSING_DISBURSEMENT_GROSS_WHEN_NET_ENTERED


def test_raises_missing_disbursement_net_when_gross_only():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            claim_type_id=ClaimType.FINAL_BILL,
            **VALID_PROFIT_COST,
            disbursement_gross=Decimal("120.00"),
        ).validate()

    assert exc.value.code == ClaimErrorCode.MISSING_DISBURSEMENT_NET_WHEN_GROSS_ENTERED


def test_raises_when_disbursement_gross_not_greater_than_net():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            claim_type_id=ClaimType.FINAL_BILL,
            **VALID_PROFIT_COST,
            disbursement_net=Decimal("120.00"),
            disbursement_gross=Decimal("120.00"),
        ).validate()

    assert exc.value.code == ClaimErrorCode.DISBURSEMENT_GROSS_NOT_GREATER_THAN_TOTAL


def test_raises_when_disbursement_gross_not_greater_than_vat_zero_plus_net():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            claim_type_id=ClaimType.FINAL_BILL,
            **VALID_PROFIT_COST,
            disbursement_net=Decimal("100.00"),
            disbursement_gross=Decimal("120.00"),
            disbursement_vat_zero=Decimal("50.00"),
        ).validate()

    assert exc.value.code == ClaimErrorCode.DISBURSEMENT_GROSS_NOT_GREATER_THAN_TOTAL


def test_valid_disbursement_with_zero_net_and_gross_equal_to_vat_zero():
    PayInFullClaim(
        claim_type_id=ClaimType.FINAL_BILL,
        **VALID_PROFIT_COST,
        disbursement_net=Decimal("0.00"),
        disbursement_gross=Decimal("50.00"),
        disbursement_vat_zero=Decimal("50.00"),
    ).validate()


def test_raises_when_disbursement_gross_less_than_vat_zero_with_zero_net():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            claim_type_id=ClaimType.FINAL_BILL,
            **VALID_PROFIT_COST,
            disbursement_net=Decimal("0.00"),
            disbursement_gross=Decimal("40.00"),
            disbursement_vat_zero=Decimal("50.00"),
        ).validate()

    assert exc.value.code == ClaimErrorCode.DISBURSEMENT_GROSS_NOT_GREATER_THAN_TOTAL


def test_valid_with_all_zero_disbursement_totals():
    PayInFullClaim(
        claim_type_id=ClaimType.FINAL_BILL,
        **VALID_PROFIT_COST,
        disbursement_net=Decimal("0.00"),
        disbursement_gross=Decimal("0.00"),
        disbursement_vat_zero=Decimal("0.00"),
    ).validate()


def test_valid_with_zero_net_and_gross_and_vat_zero_amount():
    PayInFullClaim(
        claim_type_id=ClaimType.FINAL_BILL,
        **VALID_PROFIT_COST,
        disbursement_net=Decimal("0.00"),
        disbursement_gross=Decimal("0.00"),
        disbursement_vat_zero=Decimal("50.00"),
    ).validate()


def test_valid_with_zero_net_and_gross_and_no_vat_zero():
    PayInFullClaim(
        claim_type_id=ClaimType.FINAL_BILL,
        **VALID_PROFIT_COST,
        disbursement_net=Decimal("0.00"),
        disbursement_gross=Decimal("0.00"),
    ).validate()


def test_profit_cost_error_takes_priority_over_disbursement_error():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            claim_type_id=ClaimType.FINAL_BILL,
        ).validate()

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
    assert (
        PayInFullClaim(claim_type_id=ClaimType.FINAL_BILL, **amounts).is_nil_bill
        is True
    )


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
    assert (
        PayInFullClaim(claim_type_id=ClaimType.FINAL_BILL, **amounts).is_nil_bill
        is False
    )


# Payment on account claim type (manual "pay in full" fast-track)


def test_valid_poa_profit_cost_claim_with_only_profit_cost_amounts():
    PayInFullClaim(
        claim_type_id=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type_id=POAType.PROFIT_COST,
        **VALID_PROFIT_COST,
    ).validate()


def test_raises_disbursement_not_allowed_for_poa_profit_cost_claim():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            claim_type_id=ClaimType.PAYMENT_ON_ACCOUNT,
            poa_type_id=POAType.PROFIT_COST,
            **VALID_PROFIT_COST,
            disbursement_net=Decimal("100.00"),
            disbursement_gross=Decimal("200.00"),
        ).validate()

    assert exc.value.code == ClaimErrorCode.DISBURSEMENT_NOT_ALLOWED_FOR_POA_CLAIM


@pytest.mark.parametrize(
    "poa_type", [POAType.EXPERT_COST, POAType.NON_EXPERT_DISBURSEMENT]
)
def test_valid_poa_disbursement_claim_with_only_disbursement_amounts(poa_type):
    PayInFullClaim(
        claim_type_id=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type_id=poa_type,
        **VALID_DISBURSEMENT,
    ).validate()


@pytest.mark.parametrize(
    "poa_type", [POAType.EXPERT_COST, POAType.NON_EXPERT_DISBURSEMENT]
)
def test_raises_profit_cost_not_allowed_for_poa_disbursement_claim(poa_type):
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            claim_type_id=ClaimType.PAYMENT_ON_ACCOUNT,
            poa_type_id=poa_type,
            **VALID_DISBURSEMENT,
            profit_cost_net=Decimal("1000.00"),
            profit_cost_gross=Decimal("1200.00"),
        ).validate()

    assert exc.value.code == ClaimErrorCode.PROFIT_COST_NOT_ALLOWED_FOR_POA_CLAIM


def test_poa_claim_with_no_poa_type_still_requires_profit_cost_totals():
    """Safe default: if poa_type_id is missing (shouldn't happen for a real
    POA claim), normal (final-bill-style) validation applies to both
    groups."""
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            claim_type_id=ClaimType.PAYMENT_ON_ACCOUNT,
            **VALID_DISBURSEMENT,
        ).validate()

    assert exc.value.code == ClaimErrorCode.MISSING_TOTAL_CLAIM_COST


def test_poa_claim_with_no_poa_type_still_requires_disbursement_totals():
    with pytest.raises(ClaimValidationError) as exc:
        PayInFullClaim(
            claim_type_id=ClaimType.PAYMENT_ON_ACCOUNT,
            **VALID_PROFIT_COST,
        ).validate()

    assert exc.value.code == ClaimErrorCode.MISSING_DISBURSEMENT_TOTAL


@pytest.mark.parametrize(
    ("net", "gross", "vat_zero"),
    [
        ("0.00", "150.00", "150.00"),
        ("0.00", "0.00", "150.00"),
        ("0.00", "150.00", "100.00"),
        ("1000.00", "1320.00", "120.00"),
        ("1000.00", "1200.00", "0.00"),
    ],
)
def test_submitted_disbursement_poa_claim_can_be_paid_in_full(net, gross, vat_zero):
    claim = Claim(
        claim_type_id=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type_id=POAType.EXPERT_COST,
        total_profit_cost_net=Decimal(net),
        total_profit_cost_gross=Decimal(gross),
        total_profit_cost_vat_zero=Decimal(vat_zero),
    )

    pay_in_full_claim_from_submitted_poa_claim(claim).validate()
