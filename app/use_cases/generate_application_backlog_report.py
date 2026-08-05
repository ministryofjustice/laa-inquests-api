import csv
import io
from datetime import datetime

from app.ports.application_backlog_port import ApplicationBacklogPort
from app.ports.provider_details_port import ProviderDetailsPort


class GenerateApplicationBacklogReportUseCase:
    def __init__(
        self,
        application_backlog_port: ApplicationBacklogPort,
        provider_details_port: ProviderDetailsPort,
    ) -> None:
        self.application_backlog_port = application_backlog_port
        self.provider_details_port = provider_details_port

    def execute(self) -> str:
        advocate_firms = self.provider_details_port.get_advocate_firms()
        applications = self.application_backlog_port.get_pending_applications()

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
            firm_code = application.provider.firm_code if application.provider else ""
            firm_name = advocate_firms.get(firm_code, "")

            proceeding = application.proceeding
            proceeding_code = proceeding.proceeding_id if proceeding else ""
            matter_type = proceeding.matter_type if proceeding else ""
            merits_decision = proceeding.merits_decision if proceeding else ""
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
                    proceeding_code,
                    matter_type,
                ]
            )

        return output.getvalue()
