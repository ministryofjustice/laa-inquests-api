import csv
import io
import logging
from datetime import datetime

from app.domain.constants.report_csv_headers import APPLICATION_BACKLOG_REPORT_HEADERS
from app.logging_utils import build_log_extra
from app.models.application.index import Application
from app.ports.application_backlog_port import ApplicationBacklogPort
from app.ports.provider_details_port import ProviderDetailsPort
from app.use_cases.exceptions import ReportGenerationError

logger = logging.getLogger(__name__)


class GenerateApplicationBacklogReportUseCase:
    def __init__(
        self,
        application_backlog_port: ApplicationBacklogPort,
        provider_details_port: ProviderDetailsPort,
    ) -> None:
        self.application_backlog_port = application_backlog_port
        self.provider_details_port = provider_details_port

    def execute(self) -> str:
        applications = self.application_backlog_port.get_pending_applications()
        try:
            firm_name_lookup = self._build_firm_name_lookup(applications)

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(APPLICATION_BACKLOG_REPORT_HEADERS)

            for application in applications:
                firm_code = application.provider.firm_code
                firm_name = firm_name_lookup.get(firm_code)

                if firm_name is None:
                    logger.info(
                        "Application backlog report generation failed: firm name missing",
                        extra=build_log_extra(
                            event="application_backlog_report_generation_failed",
                            firm_code=firm_code,
                            laa_reference=application.laa_reference,
                        ),
                    )
                    raise ReportGenerationError(
                        f"Firm name not found for firm code {firm_code}"
                    )

                proceeding = application.proceeding
                merits_decision = proceeding.merits_decision
                created_at = (
                    application.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    if isinstance(application.created_at, datetime)
                    else str(application.created_at)
                )

                writer.writerow(
                    [
                        str(application.laa_reference),
                        merits_decision,
                        created_at,
                        firm_name,
                        firm_code,
                        proceeding.proceeding_id,
                        proceeding.matter_type,
                    ]
                )

            logger.info(
                "Application backlog report generated",
                extra=build_log_extra(
                    event="application_backlog_report_generated",
                    application_count=len(applications),
                ),
            )
            return output.getvalue()
        except Exception:
            logger.warning(
                "Application backlog report generation failed",
                extra=build_log_extra(
                    event="application_backlog_report_generation_failed",
                    application_count=len(applications),
                ),
                exc_info=True,
            )
            raise

    def _build_firm_name_lookup(
        self, applications: list[Application]
    ) -> dict[str, str]:
        firm_codes = list({app.provider.firm_code for app in applications})
        firms = self.provider_details_port.get_firms_by_ids(firm_codes)
        return {firm["firmNumber"]: firm["firmName"] for firm in firms}
