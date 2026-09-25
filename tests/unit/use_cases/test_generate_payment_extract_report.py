from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.domain.constants.report_csv_headers import PAYMENT_EXTRACT_REPORT_HEADERS
from app.domain.payment_extract_report import (
    PaymentExtractReportSourceLine,
    PaymentLineType,
)
from app.models.claim.enums import InvoiceTypeCode, POAType, TaxCode
from app.use_cases import generate_payment_extract_report
from app.use_cases.exceptions import (
    ProviderDetailsRetrievalError,
    ReportGenerationError,
)
from app.use_cases.generate_payment_extract_report import (
    GeneratePaymentExtractReportUseCase,
)
from tests.helpers.csv_helpers import parse_csv_fieldnames, parse_csv_rows

FROM_DATE = date(2025, 3, 1)
TO_DATE = date(2025, 3, 31)
FINAL_BILL_FEES = PaymentLineType(invoice_type=InvoiceTypeCode.FINAL_BILL_FEES)
OFFICE_ID = "9Z999Z"


def _line(
    invoice_number: str = "INQC-AAAA-BBBB_001",
    firm_code: str = "ABC123",
    line_type: PaymentLineType = FINAL_BILL_FEES,
    office_id: str = OFFICE_ID,
) -> PaymentExtractReportSourceLine:
    return PaymentExtractReportSourceLine(
        invoice_number=invoice_number,
        invoice_amount=Decimal("120.5"),
        invoice_date=date(2025, 3, 10),
        tax_code=TaxCode.GB_VAT_20,
        line_type=line_type,
        firm_code=firm_code,
        office_id=office_id,
        laa_reference="INQ-123-456",
    )


def _build_use_case(
    lines: list[PaymentExtractReportSourceLine] | None = None,
    firms: list[dict] | None = None,
) -> tuple[GeneratePaymentExtractReportUseCase, MagicMock, MagicMock]:
    lines = [] if lines is None else lines
    report_port = MagicMock()
    report_port.get_payment_extract_firm_codes.return_value = sorted(
        {line.firm_code for line in lines}
    )
    report_port.get_payment_extract_line_types.return_value = list(
        {line.line_type for line in lines}
    )
    report_port.iter_payment_extract_report_lines.return_value = iter(lines)

    provider_details_port = MagicMock()
    provider_details_port.get_firms_by_ids.return_value = (
        [{"firmNumber": "ABC123", "firmName": "Test Firm"}] if firms is None else firms
    )

    use_case = GeneratePaymentExtractReportUseCase(
        payment_extract_report_port=report_port,
        provider_details_port=provider_details_port,
    )
    return use_case, report_port, provider_details_port


def _csv(chunks) -> str:
    return "".join(chunks)


class TestGeneratePaymentExtractReportUseCase:
    def test_returns_headers_only_when_no_lines(self):
        use_case, _, _ = _build_use_case(lines=[])

        content = _csv(use_case.execute(FROM_DATE, TO_DATE))

        assert parse_csv_fieldnames(content) == PAYMENT_EXTRACT_REPORT_HEADERS
        assert parse_csv_rows(content) == []

    def test_returns_row_with_formatted_values(self):
        use_case, _, _ = _build_use_case(lines=[_line()])

        rows = parse_csv_rows(_csv(use_case.execute(FROM_DATE, TO_DATE)))

        assert rows == [
            {
                "DESCRIPTION": "Profit costs",
                "INVOICE AMOUNT": "120.50",
                "INVOICE DATE": "2025-03-10",
                "INVOICE TYPE": "Inq Final Bill (Fees)",
                "INVOICE NUM": "INQC-AAAA-BBBB_001",
                "VENDOR NAME": "Test Firm",
                "VENDOR SITE CODE": OFFICE_ID,
                "CASE REFERENCE": "INQ-123-456",
                "CLIENT NAME": "",
                "TAX CODE": "GB VAT 20%",
                "MODEL NUMBER": "Profit costs",
                "PROVIDER CASE REF NO": "",
            }
        ]

    def test_uses_classification_for_each_line_type(self):
        poa_expert = PaymentLineType(
            invoice_type=InvoiceTypeCode.POA, poa_type=POAType.EXPERT_COST
        )
        use_case, _, _ = _build_use_case(
            lines=[_line("A_001"), _line("B_001", line_type=poa_expert)]
        )

        rows = parse_csv_rows(_csv(use_case.execute(FROM_DATE, TO_DATE)))

        assert [(row["DESCRIPTION"], row["MODEL NUMBER"]) for row in rows] == [
            ("Profit costs", "Profit costs"),
            ("Expert costs", "Disbursements"),
        ]

    def test_looks_up_firm_names_once_for_distinct_firm_codes(self):
        lines = [
            _line("A_001", firm_code="ABC123"),
            _line("A_002", firm_code="ABC123"),
            _line("B_001", firm_code="XYZ789"),
        ]
        use_case, _, provider_details_port = _build_use_case(
            lines=lines,
            firms=[
                {"firmNumber": "ABC123", "firmName": "Firm A"},
                {"firmNumber": "XYZ789", "firmName": "Firm X"},
            ],
        )

        rows = parse_csv_rows(_csv(use_case.execute(FROM_DATE, TO_DATE)))

        provider_details_port.get_firms_by_ids.assert_called_once_with(
            ["ABC123", "XYZ789"]
        )
        assert [row["VENDOR NAME"] for row in rows] == ["Firm A", "Firm A", "Firm X"]

    def test_skips_firm_lookup_when_no_lines(self):
        use_case, _, provider_details_port = _build_use_case(lines=[])

        _csv(use_case.execute(FROM_DATE, TO_DATE))

        provider_details_port.get_firms_by_ids.assert_not_called()

    def test_raises_before_streaming_when_firm_name_missing(self):
        use_case, report_port, _ = _build_use_case(lines=[_line()], firms=[])

        with pytest.raises(ReportGenerationError):
            use_case.execute(FROM_DATE, TO_DATE)

        report_port.iter_payment_extract_report_lines.assert_not_called()

    def test_propagates_provider_details_retrieval_error(self):
        use_case, report_port, provider_details_port = _build_use_case(lines=[_line()])
        provider_details_port.get_firms_by_ids.side_effect = (
            ProviderDetailsRetrievalError()
        )

        with pytest.raises(ProviderDetailsRetrievalError):
            use_case.execute(FROM_DATE, TO_DATE)

        report_port.iter_payment_extract_report_lines.assert_not_called()

    def test_raises_before_streaming_when_line_type_unclassifiable(self):
        poa_without_type = PaymentLineType(invoice_type=InvoiceTypeCode.POA)
        use_case, report_port, _ = _build_use_case(
            lines=[_line(line_type=poa_without_type)]
        )

        with pytest.raises(ReportGenerationError):
            use_case.execute(FROM_DATE, TO_DATE)

        report_port.iter_payment_extract_report_lines.assert_not_called()

    def test_raises_from_execute_when_lines_query_fails(self):
        use_case, report_port, _ = _build_use_case(lines=[_line()])

        def failing_lines():
            raise RuntimeError("db down")
            yield

        report_port.iter_payment_extract_report_lines.return_value = failing_lines()

        with pytest.raises(RuntimeError):
            use_case.execute(FROM_DATE, TO_DATE)

    def test_queries_with_same_created_at_range_for_all_port_calls(self):
        use_case, report_port, _ = _build_use_case(lines=[_line()])

        _csv(use_case.execute(FROM_DATE, TO_DATE))

        expected = (
            datetime(2025, 3, 1, tzinfo=UTC).replace(tzinfo=None),
            datetime(2025, 4, 1, tzinfo=UTC).replace(tzinfo=None),
        )
        for method in (
            report_port.get_payment_extract_firm_codes,
            report_port.get_payment_extract_line_types,
            report_port.iter_payment_extract_report_lines,
        ):
            method.assert_called_once_with(*expected)

    def test_caps_created_before_at_now_when_to_date_in_future(self):
        use_case, report_port, _ = _build_use_case(lines=[])
        future = datetime.now(UTC).date() + timedelta(days=30)

        _csv(use_case.execute(FROM_DATE, future))

        created_before = report_port.get_payment_extract_firm_codes.call_args.args[1]
        assert created_before <= datetime.now(UTC).replace(tzinfo=None)
        for method in (
            report_port.get_payment_extract_line_types,
            report_port.iter_payment_extract_report_lines,
        ):
            assert method.call_args.args[1] == created_before

    def test_yields_rows_in_chunks(self, monkeypatch):
        monkeypatch.setattr(generate_payment_extract_report, "ROWS_PER_CHUNK", 2)
        lines = [_line(f"A_{i:03d}") for i in range(5)]
        use_case, _, _ = _build_use_case(lines=lines)

        chunks = list(use_case.execute(FROM_DATE, TO_DATE))

        assert len(chunks) == 3
        rows = parse_csv_rows(_csv(chunks))
        assert [row["INVOICE NUM"] for row in rows] == [f"A_{i:03d}" for i in range(5)]

    def test_raises_mid_stream_when_line_has_unchecked_firm(self):
        use_case, report_port, _ = _build_use_case(lines=[_line()])
        report_port.iter_payment_extract_report_lines.return_value = iter(
            [_line(), _line("B_001", firm_code="NEW999")]
        )

        chunks = use_case.execute(FROM_DATE, TO_DATE)

        with pytest.raises(ReportGenerationError):
            _csv(chunks)
