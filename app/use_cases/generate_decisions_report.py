import csv
import io
import logging
from datetime import UTC, date, datetime, time, timedelta

from app.domain.constants.report_csv_headers import DECISIONS_REPORT_HEADERS
from app.domain.date_utils import add_calendar_months
from app.domain.decisions_report import (
    InvalidDecisionRecordError,
    build_decisions_report_row,
)
from app.logging_utils import build_log_extra
from app.ports.decisions_report_port import DecisionsReportPort
from app.use_cases.exceptions import InvalidDateRangeError, ReportGenerationError

logger = logging.getLogger(__name__)


class GenerateDecisionsReportUseCase:
    def __init__(self, decisions_report_port: DecisionsReportPort) -> None:
        self.decisions_report_port = decisions_report_port

    def execute(self, from_date: date, to_date: date) -> str:
        """Build the whole CSV or fail, so a partial report is never returned."""
        if from_date > to_date:
            raise InvalidDateRangeError(
                "The 'from' date must be on or before the 'to' date."
            )
        if to_date > add_calendar_months(from_date, 1):
            raise InvalidDateRangeError(
                "The date range must not exceed one calendar month."
            )

        decided_from = datetime.combine(from_date, time.min, tzinfo=UTC)
        decided_before = datetime.combine(
            to_date + timedelta(days=1), time.min, tzinfo=UTC
        )
        records = self.decisions_report_port.get_decisions_report_records(
            decided_from, decided_before
        )

        try:
            rows = [build_decisions_report_row(record).as_list() for record in records]
        except InvalidDecisionRecordError as exc:
            logger.error(
                "Decisions report generation failed",
                extra=build_log_extra(
                    event="decisions_report_generation_failed",
                    error_type=type(exc).__name__,
                    reason=str(exc),
                ),
            )
            raise ReportGenerationError(str(exc)) from exc

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(DECISIONS_REPORT_HEADERS)
        writer.writerows(rows)

        logger.info(
            "Decisions report generated",
            extra=build_log_extra(
                event="decisions_report_generated",
                row_count=len(rows),
            ),
        )
        return buffer.getvalue()
