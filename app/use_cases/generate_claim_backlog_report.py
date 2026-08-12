import csv
import io

from app.domain.constants.report_csv_headers import CLAIMS_BACKLOG_REPORT_HEADERS
from app.models.application.index import Application
from app.ports.claim_backlog_port import ClaimBacklogPort
from app.ports.provider_details_port import ProviderDetailsPort
from app.use_cases.exceptions import ReportGenerationError


class GenerateClaimBacklogReportUseCase:
    def __init__(
        self,
        claim_backlog_port: ClaimBacklogPort,
        provider_details_port: ProviderDetailsPort,
    ) -> None:
        self.claim_backlog_port = claim_backlog_port
        self.provider_details_port = provider_details_port

    def execute(self) -> str:
        claims = self.claim_backlog_port.get_open_claims()
        firm_name_lookup = self._build_firm_name_lookup(
            [claim.application for claim in claims]
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(CLAIMS_BACKLOG_REPORT_HEADERS)

        for claim in claims:
            application = claim.application
            firm_code = application.provider.firm_code
            firm_name = firm_name_lookup.get(firm_code)

            if firm_name is None:
                raise ReportGenerationError(
                    f"Firm name not found for firm code {firm_code}"
                )

            writer.writerow(
                [
                    str(claim.claim_id),
                    firm_name,
                    firm_code,
                    claim.submission_date.strftime("%Y-%m-%d %H:%M:%S"),
                    claim.status_id.value,
                    (
                        f"{claim.total_profit_cost_vat_zero:.2f}"
                        if claim.total_profit_cost_vat_zero is not None
                        else ""
                    ),
                    (
                        f"{claim.total_profit_cost_net:.2f}"
                        if claim.total_profit_cost_net is not None
                        else ""
                    ),
                    (
                        f"{claim.total_profit_cost_gross:.2f}"
                        if claim.total_profit_cost_gross is not None
                        else ""
                    ),
                    claim.claim_type_id.value,
                ]
            )

        return output.getvalue()

    def _build_firm_name_lookup(
        self, applications: list[Application]
    ) -> dict[str, str]:
        firm_codes = list({app.provider.firm_code for app in applications})
        firms = self.provider_details_port.get_firms_by_ids(firm_codes)
        return {firm["firmNumber"]: firm["firmName"] for firm in firms}
