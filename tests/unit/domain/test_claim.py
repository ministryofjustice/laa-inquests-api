from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.domain.constants.claim_reason_codes import (
    APPLICATION_CLAIMS_EXCEED_COST_LIMIT,
    CLAIM_EXCEEDS_SUBSTANTIVE_COST_LIMIT,
)
from app.domain.claim import Claim
from app.domain.claim_error import ClaimErrorCode, ClaimValidationError
from app.models.application.index import Application
from app.models.claim.enums import ClaimStatus, ClaimType, POAType
from app.models.claim.index import Claim as DBClaim


def test_valid_with_net_and_gross():
    claim = Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.PROFIT_COST,
        net=1000,
        gross=1200,
        vat_zero_total=None,
    )
    claim.validate_total_claim_cost()


def test_valid_with_vat_zero_only():
    claim = Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.PROFIT_COST,
        net=None,
        gross=None,
        vat_zero_total=500,
    )
    claim.validate_total_claim_cost()


def test_valid_when_gross_equals_net():
    claim = Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.PROFIT_COST,
        net=1000,
        gross=1000,
        vat_zero_total=None,
    )
    claim.validate_total_claim_cost()


def test_raises_when_vat_zero_and_net_both_provided():
    claim = Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.PROFIT_COST,
        net=1000,
        gross=None,
        vat_zero_total=500,
    )
    with pytest.raises(ClaimValidationError) as exc_info:
        claim.validate_total_claim_cost()
    assert exc_info.value.code == ClaimErrorCode.PROFIT_COST_MIXED_VAT


def test_raises_when_vat_zero_and_gross_both_provided():
    claim = Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.PROFIT_COST,
        net=None,
        gross=1200,
        vat_zero_total=500,
    )
    with pytest.raises(ClaimValidationError) as exc_info:
        claim.validate_total_claim_cost()
    assert exc_info.value.code == ClaimErrorCode.PROFIT_COST_MIXED_VAT


def test_raises_when_nothing_provided():
    claim = Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.PROFIT_COST,
        net=None,
        gross=None,
        vat_zero_total=None,
    )
    with pytest.raises(ClaimValidationError) as exc_info:
        claim.validate_total_claim_cost()
    assert exc_info.value.code == ClaimErrorCode.MISSING_TOTAL_CLAIM_COST


def test_raises_when_net_provided_without_gross():
    claim = Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.PROFIT_COST,
        net=1000,
        gross=None,
        vat_zero_total=None,
    )
    with pytest.raises(ClaimValidationError) as exc_info:
        claim.validate_total_claim_cost()
    assert exc_info.value.code == ClaimErrorCode.MISSING_GROSS_TOTAL_WHEN_NET_ENTERED


def test_raises_when_net_higher_than_gross():
    claim = Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.PROFIT_COST,
        net=1200,
        gross=1000,
        vat_zero_total=None,
    )
    with pytest.raises(ClaimValidationError) as exc_info:
        claim.validate_total_claim_cost()
    assert exc_info.value.code == ClaimErrorCode.NET_TOTAL_HIGHER_THAN_GROSS_TOTAL


def test_raises_when_net_is_negative():
    claim = Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.PROFIT_COST,
        net=-1,
        gross=1000,
        vat_zero_total=None,
    )
    with pytest.raises(ClaimValidationError) as exc_info:
        claim.validate_total_claim_cost()
    assert exc_info.value.code == ClaimErrorCode.NEGATIVE_NET_COST


def test_raises_when_non_profit_cost_has_no_totals():
    claim = Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.EXPERT_COST,
        net=None,
        gross=None,
        vat_zero_total=None,
    )
    with pytest.raises(ClaimValidationError) as exc_info:
        claim.validate_total_claim_cost()

    assert exc_info.value.code == ClaimErrorCode.MISSING_NON_PROFIT_COST_TOTAL


def test_non_profit_cost_defaults_missing_totals_to_zero():
    claim = Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.EXPERT_COST,
        net=None,
        gross=None,
        vat_zero_total=Decimal("150.00"),
    )

    claim.validate_total_claim_cost()

    assert claim.net == Decimal("0.00")
    assert claim.gross == Decimal("0.00")
    assert claim.vat_zero_total == Decimal("150.00")


def test_raises_when_non_profit_cost_net_higher_than_gross():
    claim = Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.NON_EXPERT_DISBURSEMENT,
        net=Decimal("120.00"),
        gross=Decimal("100.00"),
        vat_zero_total=None,
    )
    with pytest.raises(ClaimValidationError) as exc_info:
        claim.validate_total_claim_cost()

    assert exc_info.value.code == ClaimErrorCode.NET_TOTAL_HIGHER_THAN_GROSS_TOTAL


def test_no_validation_when_poa_type_is_none():
    claim = Claim(
        claim_type=ClaimType.FINAL_BILL,
        poa_type=None,
        net=None,
        gross=None,
        vat_zero_total=None,
    )
    claim.validate_total_claim_cost()


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


def test_should_auto_reject_for_limit_when_total_exceeds_limit():
    claim = Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.PROFIT_COST,
        net=Decimal("1000.00"),
        gross=Decimal("1200.00"),
        vat_zero_total=None,
    )
    claim.validate_total_claim_cost()

    application = MagicMock(spec=Application)
    application.proceedings = [MagicMock()]
    application.proceedings[0].substantive_cost_limitation = 1000
    decision = claim.should_auto_reject_for_limit(application)

    assert decision.should_auto_reject is True
    assert decision.reason_code == CLAIM_EXCEEDS_SUBSTANTIVE_COST_LIMIT


def test_should_not_auto_reject_for_limit_when_total_not_exceeding_limit():
    claim = Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.PROFIT_COST,
        net=Decimal("800.00"),
        gross=Decimal("1000.00"),
        vat_zero_total=None,
    )
    claim.validate_total_claim_cost()

    application = MagicMock(spec=Application)
    application.proceedings = [MagicMock()]
    application.proceedings[0].substantive_cost_limitation = 1000
    decision = claim.should_auto_reject_for_limit(application)

    assert decision.should_auto_reject is False
    assert decision.reason_code is None


def _make_domain_claim(gross=Decimal("500.00")):
    return Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.PROFIT_COST,
        net=Decimal("400.00"),
        gross=gross,
        vat_zero_total=None,
    )


def _make_application(limit=1000):
    application = MagicMock(spec=Application)
    application.proceedings = [MagicMock()]
    application.proceedings[0].substantive_cost_limitation = limit
    return application


def _make_db_claim(
    gross: Decimal, status: ClaimStatus = ClaimStatus.PENDING
) -> DBClaim:
    return DBClaim(
        laa_reference=12345,
        claim_type_id=ClaimType.PAYMENT_ON_ACCOUNT,
        total_profit_cost_gross=gross,
        status_id=status,
    )


def test_should_auto_reject_for_application_total_limit_when_sum_exceeds_limit():
    claim = _make_domain_claim(gross=Decimal("600.00"))
    existing = [_make_db_claim(Decimal("500.00"))]
    decision = claim.should_auto_reject_for_application_total_limit(
        _make_application(limit=1000), existing
    )

    assert decision.should_auto_reject is True
    assert decision.reason_code == APPLICATION_CLAIMS_EXCEED_COST_LIMIT


def test_should_not_auto_reject_for_application_total_limit_when_sum_within_limit():
    claim = _make_domain_claim(gross=Decimal("400.00"))
    existing = [_make_db_claim(Decimal("500.00"))]
    decision = claim.should_auto_reject_for_application_total_limit(
        _make_application(limit=1000), existing
    )

    assert decision.should_auto_reject is False
    assert decision.reason_code is None


def test_should_not_auto_reject_for_application_total_limit_when_no_proceedings():
    claim = _make_domain_claim(gross=Decimal("900.00"))
    application = MagicMock(spec=Application)
    application.proceedings = []
    decision = claim.should_auto_reject_for_application_total_limit(application, [])

    assert decision.should_auto_reject is False
    assert decision.reason_code is None


def test_should_not_auto_reject_for_application_total_limit_when_limit_is_none():
    claim = _make_domain_claim(gross=Decimal("900.00"))
    application = MagicMock(spec=Application)
    application.proceedings = [MagicMock()]
    application.proceedings[0].substantive_cost_limitation = None
    decision = claim.should_auto_reject_for_application_total_limit(application, [])

    assert decision.should_auto_reject is False
    assert decision.reason_code is None


def test_should_not_auto_reject_for_application_total_limit_when_gross_is_none():
    claim = _make_domain_claim(gross=None)
    decision = claim.should_auto_reject_for_application_total_limit(
        _make_application(limit=1000), []
    )

    assert decision.should_auto_reject is False
    assert decision.reason_code is None


def test_should_not_auto_reject_for_application_total_limit_when_no_existing_claims():
    claim = _make_domain_claim(gross=Decimal("900.00"))
    decision = claim.should_auto_reject_for_application_total_limit(
        _make_application(limit=1000), []
    )

    assert decision.should_auto_reject is False
    assert decision.reason_code is None


def test_should_auto_reject_for_application_total_limit_excludes_rejected_claims():
    claim = _make_domain_claim(gross=Decimal("600.00"))
    existing = [_make_db_claim(Decimal("500.00"), status=ClaimStatus.REJECTED)]
    decision = claim.should_auto_reject_for_application_total_limit(
        _make_application(limit=1000), existing
    )

    assert decision.should_auto_reject is False
    assert decision.reason_code is None


def test_should_auto_reject_for_application_total_limit_excludes_rejected_with_amendment_claims():
    claim = _make_domain_claim(gross=Decimal("600.00"))
    existing = [
        _make_db_claim(Decimal("500.00"), status=ClaimStatus.REJECTED_WITH_AMENDMENT)
    ]
    decision = claim.should_auto_reject_for_application_total_limit(
        _make_application(limit=1000), existing
    )

    assert decision.should_auto_reject is False
    assert decision.reason_code is None


def test_should_auto_reject_returns_per_claim_rejection_when_single_claim_exceeds_limit():
    claim = _make_domain_claim(gross=Decimal("1200.00"))
    decision = claim.should_auto_reject(_make_application(limit=1000), [])

    assert decision.should_auto_reject is True
    assert decision.reason_code == CLAIM_EXCEEDS_SUBSTANTIVE_COST_LIMIT


def test_should_auto_reject_returns_application_total_rejection_when_total_exceeds_but_single_claim_does_not():
    claim = _make_domain_claim(gross=Decimal("600.00"))
    existing = [_make_db_claim(Decimal("500.00"))]
    decision = claim.should_auto_reject(_make_application(limit=1000), existing)

    assert decision.should_auto_reject is True
    assert decision.reason_code == APPLICATION_CLAIMS_EXCEED_COST_LIMIT


def test_should_auto_reject_returns_no_rejection_when_neither_check_fails():
    claim = _make_domain_claim(gross=Decimal("400.00"))
    existing = [_make_db_claim(Decimal("500.00"))]
    decision = claim.should_auto_reject(_make_application(limit=1000), existing)

    assert decision.should_auto_reject is False
    assert decision.reason_code is None
