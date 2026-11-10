import csv
import io
import logging
from datetime import date

from app.domain.constants.report_csv_headers import DECISIONS_REPORT_HEADERS
from app.domain.decisions_report import (
    InvalidDecisionRecordError,
    build_decisions_report_row,
)
from app.logging_utils import build_log_extra
from app.ports.decisions_report_port import DecisionsReportPort
from app.use_cases.exceptions import ReportGenerationError
from app.use_cases.report_date_range import resolve_report_window

logger = logging.getLogger(__name__)

MAX_REPORT_RANGE_DAYS = 30


class GenerateDecisionsReportUseCase:
    def __init__(self, decisions_report_port: DecisionsReportPort) -> None:
        self.decisions_report_port = decisions_report_port

    def execute(self, from_date: date, to_date: date) -> str:
        """Build the whole CSV or fail, so a partial report is never returned."""
        decided_from, decided_before = resolve_report_window(
            from_date, to_date, MAX_REPORT_RANGE_DAYS
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
