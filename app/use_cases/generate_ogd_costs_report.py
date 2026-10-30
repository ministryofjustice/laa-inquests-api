import csv
import io
import logging
from datetime import date

from app.domain.constants.report_csv_headers import OGD_COSTS_REPORT_HEADERS
from app.domain.ogd_costs_report import (
    InvalidOgdCostsRecordError,
    build_ogd_costs_row,
)
from app.logging_utils import build_log_extra
from app.ports.claim.ogd_costs_report_port import OgdCostsReportPort
from app.use_cases.exceptions import ReportGenerationError
from app.use_cases.report_date_range import resolve_report_window

logger = logging.getLogger(__name__)

MAX_OGD_COSTS_REPORT_RANGE_DAYS = 90


class GenerateOgdCostsReportUseCase:
    def __init__(self, ogd_costs_report_port: OgdCostsReportPort) -> None:
        self.ogd_costs_report_port = ogd_costs_report_port

    def execute(self, from_date: date, to_date: date) -> str:
        """Build the whole CSV or fail, so a partial extract is never returned."""
        decided_from, decided_before = resolve_report_window(
            from_date, to_date, MAX_OGD_COSTS_REPORT_RANGE_DAYS
        )

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(OGD_COSTS_REPORT_HEADERS)
        row_count = 0

        try:
            public_bodies = (
                self.ogd_costs_report_port.get_ogd_public_bodies_by_application(
                    decided_from, decided_before
                )
            )
            for line in self.ogd_costs_report_port.iter_ogd_costs_report_lines(
                decided_from, decided_before
            ):
                bodies = public_bodies.get(line.application_id)
                if not bodies:
                    raise ReportGenerationError(
                        f"No public bodies found for application {line.application_id}"
                    )
                writer.writerow(build_ogd_costs_row(line, bodies))
                row_count += 1
        except Exception as exc:
            logger.error(
                "OGD costs report generation failed",
                extra=build_log_extra(
                    event="ogd_costs_report_generation_failed",
                    error_type=type(exc).__name__,
                    row_count=row_count,
                ),
            )
            if isinstance(exc, ReportGenerationError):
                raise
            if isinstance(exc, InvalidOgdCostsRecordError):
                raise ReportGenerationError(str(exc)) from exc
            raise ReportGenerationError("OGD costs report generation failed") from exc

        logger.info(
            "OGD costs report generated",
            extra=build_log_extra(
                event="ogd_costs_report_generated",
                row_count=row_count,
            ),
        )
        return buffer.getvalue()
