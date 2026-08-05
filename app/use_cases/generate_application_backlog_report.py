import csv
import io
from datetime import datetime

from app.models.application.index import Application
from app.ports.application_backlog_port import ApplicationBacklogPort
from app.ports.provider_details_port import ProviderDetailsPort
from app.use_cases.exceptions import ReportGenerationError


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
        firm_name_lookup = self._build_firm_name_lookup(applications)

        output = io.StringIO()
        writer = csv.writer(output)

        headers = [
            "Application Reference",
            "Current Status",
            "Application Received Date",
            "Firm Name",
            "Firm Account Number",
            "Proceeding Code",
            "Matter Type",
        ]
        writer.writerow(headers)

        for application in applications:
            firm_code = application.provider.firm_code
            firm_name = firm_name_lookup.get(firm_code)

            if firm_name is None:
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

        return output.getvalue()

    def _build_firm_name_lookup(
        self, applications: list[Application]
    ) -> dict[str, str]:
        firm_codes = list({app.provider.firm_code for app in applications})
        firms = self.provider_details_port.get_firms_by_ids(firm_codes)
        return {firm["firmNumber"]: firm["firmName"] for firm in firms}
