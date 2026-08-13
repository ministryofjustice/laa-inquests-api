from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.domain.claim import Claim, ExistingClaimSummary
from app.domain.claim_error import ClaimErrorCode, ClaimValidationError
from app.domain.claim_rejection import ClaimRejectionReason
from app.models.application.enums import MeritsDecision
from app.models.application.index import Application
from app.models.claim.enums import ClaimStatus, ClaimType, POAType


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
        net=Decimal("1100.00"),
        gross=Decimal("1200.00"),
        vat_zero_total=None,
    )
    claim.validate_total_claim_cost()

    application = MagicMock(spec=Application)
    application.proceeding = MagicMock()
    application.proceeding.substantive_cost_limitation = 1000
    reason = claim.should_auto_reject_for_limit(application)

    assert reason is ClaimRejectionReason.CLAIM_EXCEEDS_SUBSTANTIVE_COST_LIMIT


def test_should_not_auto_reject_for_limit_when_total_not_exceeding_limit():
    claim = Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.PROFIT_COST,
        net=Decimal("800.00"),
        gross=Decimal("900.00"),
        vat_zero_total=None,
    )
    claim.validate_total_claim_cost()

    application = MagicMock(spec=Application)
    application.proceeding = MagicMock()
    application.proceeding.substantive_cost_limitation = 1000
    reason = claim.should_auto_reject_for_limit(application)

    assert reason is None


def test_should_auto_reject_for_limit_uses_gross_not_net():
    claim = Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.PROFIT_COST,
        net=Decimal("800.00"),
        gross=Decimal("1200.00"),
        vat_zero_total=None,
    )
    claim.validate_total_claim_cost()

    application = MagicMock(spec=Application)
    application.proceeding = MagicMock()
    application.proceeding.substantive_cost_limitation = 1000
    reason = claim.should_auto_reject_for_limit(application)

    assert reason is ClaimRejectionReason.CLAIM_EXCEEDS_SUBSTANTIVE_COST_LIMIT


def test_should_auto_reject_for_limit_when_vat_zero_total_exceeds_limit():
    claim = Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.PROFIT_COST,
        net=None,
        gross=None,
        vat_zero_total=Decimal("1500.00"),
    )
    application = MagicMock(spec=Application)
    application.proceeding = MagicMock()
    application.proceeding.substantive_cost_limitation = 1000
    reason = claim.should_auto_reject_for_limit(application)

    assert reason is ClaimRejectionReason.CLAIM_EXCEEDS_SUBSTANTIVE_COST_LIMIT


def test_should_not_auto_reject_for_limit_when_vat_zero_total_within_limit():
    claim = Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.PROFIT_COST,
        net=None,
        gross=None,
        vat_zero_total=Decimal("500.00"),
    )
    application = MagicMock(spec=Application)
    application.proceeding = MagicMock()
    application.proceeding.substantive_cost_limitation = 1000
    reason = claim.should_auto_reject_for_limit(application)

    assert reason is None


def _make_domain_claim(gross=Decimal("500.00"), net=Decimal("400.00")):
    return Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.PROFIT_COST,
        net=net,
        gross=gross,
        vat_zero_total=None,
    )


def _make_application(limit=1000):
    application = MagicMock(spec=Application)
    application.proceeding = MagicMock()
    application.proceeding.substantive_cost_limitation = limit
    application.proceeding.certificate_start_date = None
    return application


def _make_existing_claim(
    net: Decimal | None = None,
    gross: Decimal | None = None,
    vat_zero_total: Decimal | None = None,
    status: ClaimStatus = ClaimStatus.SUBMITTED,
    poa_type: POAType | None = None,
    submission_date: datetime | None = None,
) -> ExistingClaimSummary:
    return ExistingClaimSummary(
        status=status,
        poa_type=poa_type,
        submission_date=submission_date or datetime.now(UTC),
        net=net,
        gross=gross,
        vat_zero_total=vat_zero_total,
    )


def test_should_auto_reject_for_application_total_limit_when_sum_exceeds_limit():
    claim = _make_domain_claim(gross=Decimal("600.00"))  # net defaults to 400.00
    existing = [
        _make_existing_claim(
            net=Decimal("700.00"),
            gross=Decimal("800.00"),
            status=ClaimStatus.PAY_IN_FULL,
        )
    ]
    reason = claim.should_auto_reject_for_application_total_limit(
        _make_application(limit=1000), existing
    )

    assert reason is ClaimRejectionReason.APPLICATION_CLAIMS_EXCEED_COST_LIMIT


def test_should_not_auto_reject_for_application_total_limit_when_sum_within_limit():
    claim = _make_domain_claim(gross=Decimal("400.00"))
    existing = [
        _make_existing_claim(
            net=Decimal("500.00"),
            gross=Decimal("500.00"),
            status=ClaimStatus.PAY_IN_FULL,
        )
    ]
    reason = claim.should_auto_reject_for_application_total_limit(
        _make_application(limit=1000), existing
    )

    assert reason is None


def test_should_not_auto_reject_for_application_total_limit_when_limit_is_none():
    claim = _make_domain_claim(gross=Decimal("900.00"))
    application = MagicMock(spec=Application)
    application.proceeding = MagicMock()
    application.proceeding.substantive_cost_limitation = None
    reason = claim.should_auto_reject_for_application_total_limit(application, [])

    assert reason is None


def test_should_not_auto_reject_for_application_total_limit_when_gross_is_none():
    claim = _make_domain_claim(net=None, gross=None)
    reason = claim.should_auto_reject_for_application_total_limit(
        _make_application(limit=1000), []
    )

    assert reason is None


def test_should_not_auto_reject_for_application_total_limit_when_no_existing_claims():
    claim = _make_domain_claim(gross=Decimal("900.00"))
    reason = claim.should_auto_reject_for_application_total_limit(
        _make_application(limit=1000), []
    )

    assert reason is None


def test_should_auto_reject_for_application_total_limit_excludes_rejected_claims():
    claim = _make_domain_claim(gross=Decimal("600.00"))
    existing = [
        _make_existing_claim(
            net=Decimal("500.00"), gross=Decimal("600.00"), status=ClaimStatus.REJECTED
        )
    ]
    reason = claim.should_auto_reject_for_application_total_limit(
        _make_application(limit=1000), existing
    )

    assert reason is None


def test_should_auto_reject_for_application_total_limit_excludes_rejected_with_amendment_claims():
    claim = _make_domain_claim(gross=Decimal("600.00"))
    existing = [
        _make_existing_claim(
            net=Decimal("500.00"),
            gross=Decimal("600.00"),
            status=ClaimStatus.REJECTED_WITH_AMENDMENT,
        )
    ]
    reason = claim.should_auto_reject_for_application_total_limit(
        _make_application(limit=1000), existing
    )

    assert reason is None


def test_should_auto_reject_for_application_total_limit_when_new_claim_has_only_vat_zero_total_and_sum_exceeds_limit():
    claim = Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.PROFIT_COST,
        net=None,
        gross=None,
        vat_zero_total=Decimal("600.00"),
    )
    existing = [
        ExistingClaimSummary(
            status=ClaimStatus.PAY_IN_FULL,
            poa_type=None,
            submission_date=datetime.now(UTC),
            net=None,
            gross=None,
            vat_zero_total=Decimal("500.00"),
        )
    ]
    # new vat_zero (600) + approved vat_zero (500) = 1100 > 1000
    reason = claim.should_auto_reject_for_application_total_limit(
        _make_application(limit=1000), existing
    )

    assert reason is ClaimRejectionReason.APPLICATION_CLAIMS_EXCEED_COST_LIMIT


def test_should_not_auto_reject_for_application_total_limit_when_prior_claim_not_yet_approved():
    claim = _make_domain_claim(gross=Decimal("600.00"))
    existing = [
        _make_existing_claim(
            net=Decimal("800.00"),
            gross=Decimal("900.00"),
            status=ClaimStatus.SUBMITTED,
        )
    ]
    reason = claim.should_auto_reject_for_application_total_limit(
        _make_application(limit=1000), existing
    )

    assert reason is None


def test_should_not_auto_reject_for_application_total_limit_when_prior_claim_rejected_for_exceeding():
    claim = _make_domain_claim(gross=Decimal("600.00"))
    existing = [
        _make_existing_claim(
            net=Decimal("1100.00"),
            gross=Decimal("1200.00"),
            status=ClaimStatus.REJECTED,
        )
    ]
    reason = claim.should_auto_reject_for_application_total_limit(
        _make_application(limit=1000), existing
    )

    assert reason is None


def test_should_auto_reject_for_application_total_limit_uses_gross_of_approved_claims():
    claim = _make_domain_claim(gross=Decimal("300.00"))
    existing = [
        _make_existing_claim(
            net=Decimal("500.00"),
            gross=Decimal("800.00"),
            status=ClaimStatus.PAY_IN_FULL,
        )
    ]
    reason = claim.should_auto_reject_for_application_total_limit(
        _make_application(limit=1000), existing
    )

    assert reason is ClaimRejectionReason.APPLICATION_CLAIMS_EXCEED_COST_LIMIT


def test_should_auto_reject_returns_per_claim_rejection_when_single_claim_exceeds_limit():
    claim = _make_domain_claim(net=Decimal("1100.00"), gross=Decimal("1200.00"))
    rejection = claim.should_auto_reject(_make_application(limit=1000), [])

    assert rejection.is_rejected is True
    assert (
        ClaimRejectionReason.CLAIM_EXCEEDS_SUBSTANTIVE_COST_LIMIT in rejection.reasons
    )


def test_should_auto_reject_returns_application_total_rejection_when_total_exceeds_but_single_claim_does_not():
    claim = _make_domain_claim(gross=Decimal("600.00"))  # net defaults to 400.00
    existing = [
        _make_existing_claim(
            net=Decimal("700.00"),
            gross=Decimal("800.00"),
            status=ClaimStatus.PAY_IN_FULL,
        )
    ]
    rejection = claim.should_auto_reject(_make_application(limit=1000), existing)

    assert rejection.is_rejected is True
    assert (
        ClaimRejectionReason.APPLICATION_CLAIMS_EXCEED_COST_LIMIT in rejection.reasons
    )


def test_should_auto_reject_returns_no_rejection_when_neither_check_fails():
    claim = _make_domain_claim(gross=Decimal("400.00"))
    existing = [_make_existing_claim(net=Decimal("500.00"), gross=Decimal("600.00"))]
    rejection = claim.should_auto_reject(_make_application(limit=1000), existing)

    assert rejection.is_rejected is False
    assert rejection.reasons == []


def _make_existing_profit_cost_poa(
    submission_date: datetime,
    status: ClaimStatus = ClaimStatus.SUBMITTED,
) -> ExistingClaimSummary:
    return ExistingClaimSummary(
        status=status,
        poa_type=POAType.PROFIT_COST,
        submission_date=submission_date,
        net=Decimal("500.00"),
        gross=Decimal("600.00"),
        vat_zero_total=None,
    )


def test_should_auto_reject_for_max_poa_count_when_4_submitted_accepted_exist_in_window():
    reference = datetime(2026, 7, 20, tzinfo=UTC)
    existing = [
        _make_existing_profit_cost_poa(reference - timedelta(days=30)),
        _make_existing_profit_cost_poa(reference - timedelta(days=60)),
        _make_existing_profit_cost_poa(
            reference - timedelta(days=90), status=ClaimStatus.ACCEPTED
        ),
        _make_existing_profit_cost_poa(reference - timedelta(days=120)),
    ]
    reason = _make_domain_claim().should_auto_reject_for_max_poa_count(
        existing, reference
    )

    assert reason is ClaimRejectionReason.MAX_POA_CLAIMS_EXCEEDED


def test_should_not_auto_reject_for_max_poa_count_when_only_3_exist_in_window():
    reference = datetime(2026, 7, 20, tzinfo=UTC)
    existing = [
        _make_existing_profit_cost_poa(reference - timedelta(days=30)),
        _make_existing_profit_cost_poa(reference - timedelta(days=60)),
        _make_existing_profit_cost_poa(reference - timedelta(days=90)),
    ]
    reason = _make_domain_claim().should_auto_reject_for_max_poa_count(
        existing, reference
    )

    assert reason is None


def test_should_not_auto_reject_for_max_poa_count_when_4_exist_outside_12_months():
    reference = datetime(2026, 7, 20, tzinfo=UTC)
    existing = [
        _make_existing_profit_cost_poa(reference - timedelta(days=400)),
        _make_existing_profit_cost_poa(reference - timedelta(days=400)),
        _make_existing_profit_cost_poa(reference - timedelta(days=400)),
        _make_existing_profit_cost_poa(reference - timedelta(days=400)),
    ]
    reason = _make_domain_claim().should_auto_reject_for_max_poa_count(
        existing, reference
    )

    assert reason is None


def test_should_not_auto_reject_for_max_poa_count_when_4_exist_but_rejected():
    reference = datetime(2026, 7, 20, tzinfo=UTC)
    existing = [
        _make_existing_profit_cost_poa(
            reference - timedelta(days=30), status=ClaimStatus.REJECTED
        ),
        _make_existing_profit_cost_poa(
            reference - timedelta(days=60), status=ClaimStatus.REJECTED
        ),
        _make_existing_profit_cost_poa(
            reference - timedelta(days=90),
            status=ClaimStatus.REJECTED_WITH_AMENDMENT,
        ),
        _make_existing_profit_cost_poa(
            reference - timedelta(days=120), status=ClaimStatus.REJECTED
        ),
    ]
    reason = _make_domain_claim().should_auto_reject_for_max_poa_count(
        existing, reference
    )

    assert reason is None


def test_should_not_auto_reject_for_max_poa_count_when_4_exist_but_one_rejected():
    reference = datetime(2026, 7, 20, tzinfo=UTC)
    existing = [
        _make_existing_profit_cost_poa(
            reference - timedelta(days=30), status=ClaimStatus.SUBMITTED
        ),
        _make_existing_profit_cost_poa(
            reference - timedelta(days=60), status=ClaimStatus.ACCEPTED
        ),
        _make_existing_profit_cost_poa(
            reference - timedelta(days=90), status=ClaimStatus.SUBMITTED
        ),
        _make_existing_profit_cost_poa(
            reference - timedelta(days=120), status=ClaimStatus.REJECTED
        ),
    ]
    reason = _make_domain_claim().should_auto_reject_for_max_poa_count(
        existing, reference
    )

    assert reason is None


def test_should_not_auto_reject_for_max_poa_count_when_claim_is_not_profit_cost():
    reference = datetime(2026, 7, 20, tzinfo=UTC)
    claim = Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.EXPERT_COST,
        net=Decimal("500.00"),
        gross=Decimal("500.00"),
        vat_zero_total=None,
    )
    existing = [
        _make_existing_profit_cost_poa(reference - timedelta(days=30)),
        _make_existing_profit_cost_poa(reference - timedelta(days=60)),
        _make_existing_profit_cost_poa(reference - timedelta(days=90)),
        _make_existing_profit_cost_poa(reference - timedelta(days=120)),
    ]
    reason = claim.should_auto_reject_for_max_poa_count(existing, reference)

    assert reason is None


def test_should_not_auto_reject_for_max_poa_count_with_no_existing_claims():
    reference = datetime(2026, 7, 20, tzinfo=UTC)
    reason = _make_domain_claim().should_auto_reject_for_max_poa_count([], reference)

    assert reason is None


def test_should_auto_reject_returns_all_applicable_reasons_when_multiple_conditions_triggered():
    reference = datetime(2026, 7, 20, tzinfo=UTC)
    claim = _make_domain_claim(
        net=Decimal("1100.00"), gross=Decimal("1200.00")
    )  # triggers cost limit checks
    existing = [
        _make_existing_profit_cost_poa(reference - timedelta(days=30)),
        _make_existing_profit_cost_poa(reference - timedelta(days=60)),
        _make_existing_profit_cost_poa(reference - timedelta(days=90)),
        _make_existing_profit_cost_poa(reference - timedelta(days=120)),
    ]
    rejection = claim.should_auto_reject(
        _make_application(limit=1000), existing, reference
    )

    assert rejection.is_rejected is True
    assert ClaimRejectionReason.MAX_POA_CLAIMS_EXCEEDED in rejection.reasons
    assert (
        ClaimRejectionReason.CLAIM_EXCEEDS_SUBSTANTIVE_COST_LIMIT in rejection.reasons
    )
    assert (
        ClaimRejectionReason.APPLICATION_CLAIMS_EXCEED_COST_LIMIT in rejection.reasons
    )


def _make_application_with_certificate(start: date | None, limit=1000000):
    application = MagicMock(spec=Application)
    proceeding = MagicMock()
    proceeding.substantive_cost_limitation = limit
    proceeding.certificate_start_date = start
    application.proceeding = proceeding
    return application


def test_should_auto_reject_early_profit_cost_poa_claim_made_during_3_month_certificate_probationary_period():
    claim = _make_domain_claim(gross=Decimal("500.00"))
    application = _make_application_with_certificate(date(2026, 5, 1))
    reference = datetime(2026, 7, 15, tzinfo=UTC)  # < 3 calendar months

    reason = claim.should_auto_reject_for_early_profit_cost_poa(application, reference)

    assert reason is ClaimRejectionReason.PROFIT_COST_POA_CLAIM_SUBMITTED_TOO_EARLY


def test_should_not_auto_reject_early_profit_cost_poa_on_exact_3_month_boundary():
    claim = _make_domain_claim(gross=Decimal("500.00"))
    application = _make_application_with_certificate(date(2026, 5, 1))
    reference = datetime(2026, 8, 1, tzinfo=UTC)  # exactly 3 calendar months

    reason = claim.should_auto_reject_for_early_profit_cost_poa(application, reference)

    assert reason is None


def test_should_not_auto_reject_early_profit_cost_poa_when_after_3_months():
    claim = _make_domain_claim(gross=Decimal("500.00"))
    application = _make_application_with_certificate(date(2026, 5, 1))
    reference = datetime(2026, 9, 1, tzinfo=UTC)

    reason = claim.should_auto_reject_for_early_profit_cost_poa(application, reference)

    assert reason is None


def test_should_not_auto_reject_early_profit_cost_poa_when_not_profit_cost():
    claim = Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.EXPERT_COST,
        net=None,
        gross=None,
        vat_zero_total=Decimal("500.00"),
    )
    application = _make_application_with_certificate(date(2026, 5, 1))
    reference = datetime(2026, 5, 15, tzinfo=UTC)

    reason = claim.should_auto_reject_for_early_profit_cost_poa(application, reference)

    assert reason is None


def test_should_auto_reject_aggregates_early_profit_cost_poa_reason():
    claim = _make_domain_claim(gross=Decimal("500.00"))
    application = _make_application_with_certificate(date(2026, 5, 1), limit=1000000)
    reference = datetime(2026, 5, 15, tzinfo=UTC)

    rejection = claim.should_auto_reject(application, [], reference)

    assert rejection.is_rejected is True
    assert (
        ClaimRejectionReason.PROFIT_COST_POA_CLAIM_SUBMITTED_TOO_EARLY
        in rejection.reasons
    )


def test_is_eligible_for_auto_approval_when_payment_on_account_total_is_50000():
    claim = Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.PROFIT_COST,
        net=Decimal("50000.00"),
        gross=Decimal("50000.00"),
        vat_zero_total=None,
    )
    application = _make_application_with_certificate(start=None)
    application.status = "LIVE"
    application.overall_decision = MeritsDecision.GRANTED

    assert claim.is_eligible_for_auto_approval(application) is True


def test_is_not_eligible_for_auto_approval_when_total_exceeds_50000():
    claim = Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.PROFIT_COST,
        net=Decimal("50000.01"),
        gross=Decimal("50000.01"),
        vat_zero_total=None,
    )
    application = _make_application_with_certificate(start=None)
    application.status = "LIVE"
    application.overall_decision = MeritsDecision.GRANTED

    assert claim.is_eligible_for_auto_approval(application) is False


def test_is_not_eligible_for_auto_approval_when_application_status_withdrawn():
    claim = Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.PROFIT_COST,
        net=Decimal("50000.00"),
        gross=Decimal("50000.00"),
        vat_zero_total=None,
    )
    application = _make_application_with_certificate(start=None)
    application.status = "WITHDRAWN"
    application.overall_decision = MeritsDecision.GRANTED

    assert claim.is_eligible_for_auto_approval(application) is False


def test_is_not_eligible_for_auto_approval_when_merits_decision_pending():
    claim = Claim(
        claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        poa_type=POAType.PROFIT_COST,
        net=Decimal("50000.00"),
        gross=Decimal("50000.00"),
        vat_zero_total=None,
    )
    application = _make_application_with_certificate(start=None)
    application.status = "LIVE"
    application.overall_decision = MeritsDecision.PENDING

    assert claim.is_eligible_for_auto_approval(application) is False


def test_is_not_eligible_for_auto_approval_when_claim_is_not_payment_on_account():
    claim = Claim(
        claim_type=ClaimType.FINAL_BILL,
        poa_type=None,
        net=Decimal("50000.00"),
        gross=Decimal("50000.00"),
        vat_zero_total=None,
    )
    application = _make_application_with_certificate(start=None)
    application.status = "LIVE"
    application.overall_decision = MeritsDecision.GRANTED

    assert claim.is_eligible_for_auto_approval(application) is False
