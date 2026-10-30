from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.domain.ogd_costs_report import OgdCostsReportSourceLine
from app.models.application.enums import PublicBodyId
from app.models.claim.enums import (
    ClaimDecisionStatus,
    ClaimType,
    InvoiceTypeCode,
    TaxCode,
)
from app.use_cases.exceptions import InvalidDateRangeError, ReportGenerationError
from app.use_cases.generate_ogd_costs_report import GenerateOgdCostsReportUseCase
from tests.helpers.csv_helpers import parse_csv_fieldnames, parse_csv_rows

FROM_DATE = date(2025, 3, 1)
TO_DATE = date(2025, 3, 31)
OGD_COSTS_REPORT_HEADERS = [
    "Claim Decision Date",
    "Claim Decision",
    "Bill Type",
    "Public Body(ies)",
    "Legal Aid Reference",
    "Invoice Number",
    "Invoice Amount",
    "Tax Code",
    "Name of Deceased",
    "Date of Death",
]


def _line(
    invoice_number: str = "INQC-AAAA-BBBB_001", application_id: int = 1, **overrides
) -> OgdCostsReportSourceLine:
    defaults = {
        "application_id": application_id,
        "claim_decision_date": datetime(2025, 3, 15, 12, 0, tzinfo=UTC),
        "claim_decision": ClaimDecisionStatus.PAY_IN_FULL,
        "invoice_type": InvoiceTypeCode.FINAL_BILL_FEES,
        "claim_type": ClaimType.FINAL_BILL,
        "laa_reference": "INQ-123-456",
        "invoice_number": invoice_number,
        "invoice_amount": Decimal("120.5"),
        "tax_code": TaxCode.GB_VAT_20,
        "deceased_first_name": "Jane",
        "deceased_last_name": "Doe",
        "deceased_date_of_death": "2025-01-02",
    }
    return OgdCostsReportSourceLine(**(defaults | overrides))


def _build_use_case(
    lines: list[OgdCostsReportSourceLine] | None = None,
    public_bodies: dict[int, list[PublicBodyId]] | None = None,
) -> tuple[GenerateOgdCostsReportUseCase, MagicMock]:
    port = MagicMock()
    port.get_ogd_public_bodies_by_application.return_value = (
        {1: [PublicBodyId.HOME_OFFICE]} if public_bodies is None else public_bodies
    )
    port.iter_ogd_costs_report_lines.return_value = iter(lines or [])
    return GenerateOgdCostsReportUseCase(ogd_costs_report_port=port), port


class TestGenerateOgdCostsReportUseCase:
    def test_returns_headers_only_when_no_lines(self):
        use_case, _ = _build_use_case(lines=[])

        content = use_case.execute(FROM_DATE, TO_DATE)

        assert parse_csv_fieldnames(content) == OGD_COSTS_REPORT_HEADERS
        assert parse_csv_rows(content) == []

    def test_passes_inclusive_utc_window_to_port(self):
        use_case, port = _build_use_case()

        use_case.execute(FROM_DATE, TO_DATE)

        window = (
            datetime(2025, 3, 1, tzinfo=UTC),
            datetime(2025, 4, 1, tzinfo=UTC),
        )
        port.get_ogd_public_bodies_by_application.assert_called_once_with(*window)
        port.iter_ogd_costs_report_lines.assert_called_once_with(*window)

    @pytest.mark.parametrize(
        ("from_date", "to_date"),
        [
            (date(2025, 1, 1), date(2025, 4, 1)),
            (date(2025, 4, 1), date(2025, 3, 31)),
        ],
    )
    def test_rejects_invalid_range_without_calling_the_port(self, from_date, to_date):
        use_case, port = _build_use_case()

        with pytest.raises(InvalidDateRangeError):
            use_case.execute(from_date, to_date)

        port.get_ogd_public_bodies_by_application.assert_not_called()
        port.iter_ogd_costs_report_lines.assert_not_called()

    def test_renders_one_row_per_line_using_public_bodies_lookup(self):
        use_case, _ = _build_use_case(
            lines=[
                _line("A_001", application_id=1),
                _line("A_002", application_id=1),
                _line("B_001", application_id=2),
            ],
            public_bodies={
                1: [PublicBodyId.HOME_OFFICE],
                2: [PublicBodyId.MINISTRY_OF_JUSTICE, PublicBodyId.CABINET_OFFICE],
            },
        )

        rows = parse_csv_rows(use_case.execute(FROM_DATE, TO_DATE))

        assert [(row["Invoice Number"], row["Public Body(ies)"]) for row in rows] == [
            ("A_001", "Home Office"),
            ("A_002", "Home Office"),
            ("B_001", "Cabinet Office; Ministry of Justice"),
        ]

    def test_fails_when_application_has_no_public_bodies(self):
        use_case, _ = _build_use_case(lines=[_line(application_id=7)], public_bodies={})

        with pytest.raises(ReportGenerationError):
            use_case.execute(FROM_DATE, TO_DATE)

    def test_fails_without_partial_output_when_port_fails_part_way(self):
        def lines_then_failure():
            yield _line("A_001")
            raise RuntimeError("database connection lost")

        use_case, port = _build_use_case()
        port.iter_ogd_costs_report_lines.return_value = lines_then_failure()

        with pytest.raises(ReportGenerationError):
            use_case.execute(FROM_DATE, TO_DATE)

    def test_fails_when_a_line_cannot_be_rendered(self):
        use_case, _ = _build_use_case(
            lines=[_line(deceased_date_of_death="01-01-2026")]
        )

        with pytest.raises(ReportGenerationError):
            use_case.execute(FROM_DATE, TO_DATE)
