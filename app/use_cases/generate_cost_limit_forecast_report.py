import csv
import io
import logging
from datetime import UTC, date, datetime

from app.domain.constants.report_csv_headers import COST_LIMIT_FORECAST_REPORT_HEADERS
from app.domain.cost_limit_forecast_report import build_cost_limit_forecast_row
from app.logging_utils import build_log_extra
from app.ports.cost_limit_forecast_report_port import CostLimitForecastReportPort
from app.use_cases.exceptions import ReportGenerationError

logger = logging.getLogger(__name__)


class GenerateCostLimitForecastReportUseCase:
    def __init__(self, report_port: CostLimitForecastReportPort) -> None:
        self.report_port = report_port

    def execute(self, report_date: date | None = None) -> str:
        """Build the whole CSV or fail, so a partial extract is never returned."""
        report_date = report_date or datetime.now(UTC).date()

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(COST_LIMIT_FORECAST_REPORT_HEADERS)
        row_count = 0

        try:
            for candidate in self.report_port.iter_forecast_candidates():
                row = build_cost_limit_forecast_row(candidate, report_date)
                if row is not None:
                    writer.writerow(row)
                    row_count += 1
        except Exception as exc:
            logger.error(
                "Cost limit forecast report generation failed",
                extra=build_log_extra(
                    event="cost_limit_forecast_report_generation_failed",
                    error_type=type(exc).__name__,
                    row_count=row_count,
                ),
            )
            raise ReportGenerationError(
                "Cost limit forecast report generation failed"
            ) from exc

        logger.info(
            "Cost limit forecast report generated",
            extra=build_log_extra(
                event="cost_limit_forecast_report_generated",
                row_count=row_count,
            ),
        )
        return buffer.getvalue()
