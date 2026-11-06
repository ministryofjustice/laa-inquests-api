from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.domain.cost_limit_forecast_report import (
    CostLimitForecastCandidate,
    ForecastClaim,
)
from app.models.application.enums import MeritsDecision, PublicBodyId
from app.models.claim.enums import ClaimStatus, ClaimType
from app.use_cases.exceptions import ReportGenerationError
from app.use_cases.generate_cost_limit_forecast_report import (
    GenerateCostLimitForecastReportUseCase,
)
from tests.helpers.csv_helpers import parse_csv_fieldnames, parse_csv_rows

REPORT_DATE = date(2026, 11, 3)
COST_LIMIT_FORECAST_REPORT_HEADERS = [
    "Case Reference",
    "Public Body(ies)",
    "Cost Limit",
    "Total Remaining Cost Limit Value",
    "Certificate Effective Date",
]


def _candidate(laa_reference: str = "INQ-123-456", **overrides):
    defaults = {
        "application_id": 1,
        "laa_reference": laa_reference,
        "application_status": "LIVE",
        "merits_decision": MeritsDecision.GRANTED,
        "certificate_end_date": None,
        "cost_limit": 10000,
        "certificate_effective_date": date(2026, 1, 5),
        "claims": (),
        "public_bodies": (PublicBodyId.HOME_OFFICE,),
    }
    return CostLimitForecastCandidate(**(defaults | overrides))


def _build_use_case(
    candidates: list[CostLimitForecastCandidate] | None = None,
) -> tuple[GenerateCostLimitForecastReportUseCase, MagicMock]:
    port = MagicMock()
    port.iter_forecast_candidates.return_value = iter(candidates or [])
    return GenerateCostLimitForecastReportUseCase(report_port=port), port


class TestGenerateCostLimitForecastReportUseCase:
    def test_returns_headers_only_when_there_are_no_candidates(self):
        use_case, _ = _build_use_case()

        content = use_case.execute(REPORT_DATE)

        assert parse_csv_fieldnames(content) == COST_LIMIT_FORECAST_REPORT_HEADERS
        assert parse_csv_rows(content) == []

    def test_asks_the_port_for_every_certificate_without_a_date_filter(self):
        use_case, port = _build_use_case()

        use_case.execute(REPORT_DATE)

        port.iter_forecast_candidates.assert_called_once_with()

    def test_writes_one_row_per_qualifying_candidate_in_port_order(self):
        use_case, _ = _build_use_case(
            [
                _candidate("INQ-000-001"),
                _candidate("INQ-000-002", application_status="CANCELLED"),
                _candidate(
                    "INQ-000-003",
                    claims=(
                        ForecastClaim(
                            ClaimType.PAYMENT_ON_ACCOUNT,
                            ClaimStatus.PAY_IN_FULL,
                            Decimal("2500.00"),
                            None,
                        ),
                    ),
                ),
            ]
        )

        rows = parse_csv_rows(use_case.execute(REPORT_DATE))

        assert [
            (row["Case Reference"], row["Total Remaining Cost Limit Value"])
            for row in rows
        ] == [("INQ-000-001", "10000.00"), ("INQ-000-003", "7500.00")]

    def test_defaults_the_report_date_to_today_in_utc(self, monkeypatch):
        class FixedDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 11, 3, 9, 0, tzinfo=tz or UTC)

        monkeypatch.setattr(
            "app.use_cases.generate_cost_limit_forecast_report.datetime",
            FixedDatetime,
        )
        use_case, _ = _build_use_case(
            [
                _candidate("INQ-000-001", certificate_end_date=date(2026, 11, 3)),
                _candidate("INQ-000-002", certificate_end_date=date(2026, 11, 2)),
            ]
        )

        rows = parse_csv_rows(use_case.execute())

        assert [row["Case Reference"] for row in rows] == ["INQ-000-001"]

    def test_fails_without_partial_output_when_port_fails_part_way(self):
        def candidates_then_failure():
            yield _candidate("INQ-000-001")
            raise RuntimeError("database connection lost")

        use_case, port = _build_use_case()
        port.iter_forecast_candidates.return_value = candidates_then_failure()

        with pytest.raises(ReportGenerationError):
            use_case.execute(REPORT_DATE)

    def test_fails_when_a_candidate_cannot_be_rendered(self):
        use_case, _ = _build_use_case([_candidate(certificate_effective_date=None)])

        with pytest.raises(ReportGenerationError):
            use_case.execute(REPORT_DATE)
