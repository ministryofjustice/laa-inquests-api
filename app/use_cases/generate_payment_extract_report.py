import csv
import io
import itertools
import logging
from collections.abc import Iterator
from datetime import UTC, date, datetime, time, timedelta

from app.domain.constants.report_csv_headers import PAYMENT_EXTRACT_REPORT_HEADERS
from app.domain.payment_extract_report import (
    PaymentExtractReportSourceLine,
    PaymentLineClassification,
    PaymentLineType,
    UnclassifiablePaymentLineError,
    classify_payment_line,
)
from app.logging_utils import build_log_extra
from app.ports.claim.payment_extract_report_port import PaymentExtractReportPort
from app.ports.provider_details_port import ProviderDetailsPort
from app.use_cases.exceptions import ReportGenerationError

logger = logging.getLogger(__name__)

ROWS_PER_CHUNK = 500


class GeneratePaymentExtractReportUseCase:
    def __init__(
        self,
        payment_extract_report_port: PaymentExtractReportPort,
        provider_details_port: ProviderDetailsPort,
    ) -> None:
        self.payment_extract_report_port = payment_extract_report_port
        self.provider_details_port = provider_details_port

    def execute(self, from_date: date, to_date: date) -> Iterator[str]:
        """Validate all lookups up front, then return a lazy CSV chunk stream."""
        created_from = datetime.combine(from_date, time.min)
        # created_at is stored as naive UTC; capping at now keeps pre-checks and stream on the same rows.
        created_before = min(
            datetime.combine(to_date + timedelta(days=1), time.min),
            datetime.now(UTC).replace(tzinfo=None),
        )

        firm_names = self._build_firm_name_lookup(created_from, created_before)
        classifications = self._build_classification_lookup(
            created_from, created_before
        )

        lines = iter(
            self.payment_extract_report_port.iter_payment_extract_report_lines(
                created_from, created_before
            )
        )
        # Run the query now so DB failures surface before the response starts.
        first_line = next(lines, None)
        if first_line is not None:
            lines = itertools.chain([first_line], lines)

        return self._stream_csv(lines, firm_names, classifications)

    def _build_firm_name_lookup(
        self, created_from: datetime, created_before: datetime
    ) -> dict[str, str]:
        firm_codes = self.payment_extract_report_port.get_payment_extract_firm_codes(
            created_from, created_before
        )
        if not firm_codes:
            return {}

        firms = self.provider_details_port.get_firms_by_ids(firm_codes)
        firm_names = {firm["firmNumber"]: firm["firmName"] for firm in firms}

        for firm_code in firm_codes:
            if firm_names.get(firm_code) is None:
                logger.warning(
                    "Payment extract report generation failed: firm name missing",
                    extra=build_log_extra(
                        event="payment_extract_report_generation_failed",
                        firm_code=firm_code,
                    ),
                )
                raise ReportGenerationError(
                    f"Firm name not found for firm code {firm_code}"
                )
        return firm_names

    def _build_classification_lookup(
        self, created_from: datetime, created_before: datetime
    ) -> dict[PaymentLineType, PaymentLineClassification]:
        line_types = self.payment_extract_report_port.get_payment_extract_line_types(
            created_from, created_before
        )
        classifications: dict[PaymentLineType, PaymentLineClassification] = {}
        for line_type in line_types:
            try:
                classifications[line_type] = classify_payment_line(line_type)
            except UnclassifiablePaymentLineError as exc:
                logger.warning(
                    "Payment extract report generation failed: unclassifiable line",
                    extra=build_log_extra(
                        event="payment_extract_report_generation_failed",
                        invoice_type=line_type.invoice_type.value,
                    ),
                )
                raise ReportGenerationError(str(exc)) from exc
        return classifications

    def _stream_csv(
        self,
        lines: Iterator[PaymentExtractReportSourceLine],
        firm_names: dict[str, str],
        classifications: dict[PaymentLineType, PaymentLineClassification],
    ) -> Iterator[str]:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(PAYMENT_EXTRACT_REPORT_HEADERS)
        row_count = 0

        try:
            for line in lines:
                writer.writerow(self._build_row(line, firm_names, classifications))
                row_count += 1
                if row_count % ROWS_PER_CHUNK == 0:
                    yield _drain(buffer)

            remaining = _drain(buffer)
            if remaining:
                yield remaining
        except Exception:
            logger.exception(
                "Payment extract report stream failed",
                extra=build_log_extra(
                    event="payment_extract_report_stream_failed",
                    row_count=row_count,
                ),
            )
            raise

        logger.info(
            "Payment extract report generated",
            extra=build_log_extra(
                event="payment_extract_report_generated",
                row_count=row_count,
            ),
        )

    @staticmethod
    def _build_row(
        line: PaymentExtractReportSourceLine,
        firm_names: dict[str, str],
        classifications: dict[PaymentLineType, PaymentLineClassification],
    ) -> list[str]:
        firm_name = firm_names.get(line.firm_code)
        classification = classifications.get(line.line_type)
        if firm_name is None or classification is None:
            raise ReportGenerationError(
                f"Payment extract line {line.invoice_number} was not pre-checked"
            )

        return [
            classification.description,
            f"{line.invoice_amount:.2f}",
            line.invoice_date.isoformat(),
            line.line_type.invoice_type.value,
            line.invoice_number,
            firm_name,
            line.office_id,
            line.laa_reference,
            "",
            line.tax_code.value,
            classification.model_number,
            "",
        ]


def _drain(buffer: io.StringIO) -> str:
    content = buffer.getvalue()
    buffer.seek(0)
    buffer.truncate(0)
    return content
