from datetime import date
from decimal import Decimal

import pytest

from app.domain.cost_limit_forecast_report import (
    CostLimitForecastCandidate,
    ForecastClaim,
    InvalidCostLimitForecastRecordError,
    build_cost_limit_forecast_row,
)
from app.models.application.enums import MeritsDecision, PublicBodyId
from app.models.claim.enums import ClaimStatus, ClaimType

REPORT_DATE = date(2026, 11, 3)


def _claim(
    status: ClaimStatus = ClaimStatus.PAY_IN_FULL,
    claim_type: ClaimType = ClaimType.PAYMENT_ON_ACCOUNT,
    gross: str | None = "1000.00",
    vat_zero_total: str | None = None,
) -> ForecastClaim:
    return ForecastClaim(
        claim_type=claim_type,
        status=status,
        gross=Decimal(gross) if gross is not None else None,
        vat_zero_total=Decimal(vat_zero_total) if vat_zero_total is not None else None,
    )


def _candidate(**overrides) -> CostLimitForecastCandidate:
    defaults = {
        "application_id": 1,
        "laa_reference": "INQ-123-456",
        "application_status": "LIVE",
        "merits_decision": MeritsDecision.GRANTED,
        "certificate_end_date": None,
        "cost_limit": 10000,
        "certificate_effective_date": date(2026, 1, 5),
        "claims": (),
        "public_bodies": (PublicBodyId.HOME_OFFICE,),
    }
    return CostLimitForecastCandidate(**(defaults | overrides))


class TestEligibility:
    def test_live_granted_certificate_without_end_date_qualifies(self):
        assert build_cost_limit_forecast_row(_candidate(), REPORT_DATE) is not None

    @pytest.mark.parametrize(
        "overrides",
        [
            {"application_status": "CANCELLED"},
            {"merits_decision": MeritsDecision.SUBMITTED},
            {"merits_decision": MeritsDecision.REFUSED},
            {"certificate_end_date": date(2026, 11, 2)},
        ],
        ids=["not-live", "not-granted", "refused", "ended-before-report-date"],
    )
    def test_certificate_that_is_not_live_does_not_qualify(self, overrides):
        assert (
            build_cost_limit_forecast_row(_candidate(**overrides), REPORT_DATE) is None
        )

    @pytest.mark.parametrize("end_date", [date(2026, 11, 3), date(2030, 1, 1)])
    def test_certificate_ending_on_or_after_report_date_qualifies(self, end_date):
        candidate = _candidate(certificate_end_date=end_date)

        assert build_cost_limit_forecast_row(candidate, REPORT_DATE) is not None


class TestFinalBill:
    def test_pay_in_full_final_bill_excludes_the_certificate(self):
        candidate = _candidate(
            claims=(_claim(ClaimStatus.PAY_IN_FULL, ClaimType.FINAL_BILL),)
        )

        assert build_cost_limit_forecast_row(candidate, REPORT_DATE) is None

    @pytest.mark.parametrize(
        ("claim_type", "status"),
        [
            (ClaimType.FINAL_BILL, ClaimStatus.SUBMITTED),
            (ClaimType.FINAL_BILL, ClaimStatus.REJECTED),
            (ClaimType.PAYMENT_ON_ACCOUNT, ClaimStatus.PAY_IN_FULL),
            (ClaimType.NIL_BILL, ClaimStatus.SUBMITTED),
        ],
    )
    def test_other_claims_do_not_exclude_the_certificate(self, claim_type, status):
        candidate = _candidate(claims=(_claim(status, claim_type),))

        assert build_cost_limit_forecast_row(candidate, REPORT_DATE) is not None


class TestRemainingCostLimit:
    def test_remaining_equals_cost_limit_when_there_are_no_claims(self):
        row = build_cost_limit_forecast_row(_candidate(), REPORT_DATE)

        assert row[3] == "10000.00"

    def test_only_pay_in_full_claims_reduce_the_remaining_value(self):
        candidate = _candidate(
            claims=(
                _claim(ClaimStatus.PAY_IN_FULL, gross="3000.00"),
                _claim(ClaimStatus.PAY_IN_FULL, gross="250.50"),
                _claim(ClaimStatus.SUBMITTED, gross="500.00"),
                _claim(ClaimStatus.REJECTED, gross="700.00"),
                _claim(ClaimStatus.REJECTED_WITH_AMENDMENT, gross="90.00"),
            )
        )

        row = build_cost_limit_forecast_row(candidate, REPORT_DATE)

        assert row[3] == "6749.50"

    def test_claim_with_only_a_zero_vat_total_is_deducted_by_that_total(self):
        candidate = _candidate(
            claims=(_claim(gross="0.00", vat_zero_total="400.00"),),
        )

        row = build_cost_limit_forecast_row(candidate, REPORT_DATE)

        assert row[3] == "9600.00"

    @pytest.mark.parametrize("gross", ["10000.00", "10000.01"])
    def test_certificate_with_no_remaining_value_does_not_qualify(self, gross):
        candidate = _candidate(claims=(_claim(gross=gross),))

        assert build_cost_limit_forecast_row(candidate, REPORT_DATE) is None

    @pytest.mark.parametrize("cost_limit", [0, None])
    def test_certificate_without_a_cost_limit_does_not_qualify(self, cost_limit):
        candidate = _candidate(cost_limit=cost_limit)

        assert build_cost_limit_forecast_row(candidate, REPORT_DATE) is None


class TestRowFormatting:
    def test_row_has_the_required_columns_in_order(self):
        candidate = _candidate(
            claims=(_claim(gross="2500.5"),),
            certificate_effective_date=date(2026, 1, 5),
        )

        assert build_cost_limit_forecast_row(candidate, REPORT_DATE) == [
            "INQ-123-456",
            "Home Office",
            "10000.00",
            "7499.50",
            "05-01-2026",
        ]

    def test_public_bodies_are_sorted_and_separated_by_semicolon_and_space(self):
        candidate = _candidate(
            public_bodies=(
                PublicBodyId.MINISTRY_OF_JUSTICE,
                PublicBodyId.CABINET_OFFICE,
            )
        )

        row = build_cost_limit_forecast_row(candidate, REPORT_DATE)

        assert row[1] == "Cabinet Office; Ministry of Justice"


class TestPublicBodies:
    def test_qualifying_certificate_without_public_bodies_is_invalid(self):
        candidate = _candidate(public_bodies=())

        with pytest.raises(InvalidCostLimitForecastRecordError):
            build_cost_limit_forecast_row(candidate, REPORT_DATE)

    def test_certificate_without_public_bodies_that_does_not_qualify_is_ignored(self):
        candidate = _candidate(public_bodies=(), application_status="CANCELLED")

        assert build_cost_limit_forecast_row(candidate, REPORT_DATE) is None
