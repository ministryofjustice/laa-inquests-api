import csv
import io

from app.domain.constants.report_csv_headers import CLAIMS_BACKLOG_REPORT_HEADERS
from app.models.application.index import Application
from app.models.claim.index import Claim
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.claim_backlog_port import ClaimBacklogPort
from app.ports.provider_details_port import ProviderDetailsPort
from app.use_cases.exceptions import ReportGenerationError


class GenerateClaimBacklogReportUseCase:
    def __init__(
        self,
        claim_backlog_port: ClaimBacklogPort,
        application_lookup_port: ApplicationLookupPort,
        provider_details_port: ProviderDetailsPort,
    ) -> None:
        self.claim_backlog_port = claim_backlog_port
        self.application_lookup_port = application_lookup_port
        self.provider_details_port = provider_details_port

    def execute(self) -> str:
        claims = self.claim_backlog_port.get_open_claims()
        application_lookup = self._build_application_lookup(claims)
        firm_name_lookup = self._build_firm_name_lookup(
            list(application_lookup.values())
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(CLAIMS_BACKLOG_REPORT_HEADERS)

        for claim in claims:
            application = application_lookup[claim.claim_id]
            firm_code = application.provider.firm_code
            firm_name = firm_name_lookup.get(firm_code)

            if firm_name is None:
                raise ReportGenerationError(
                    f"Firm name not found for firm code {firm_code}"
                )

            proceeding = application.proceeding

            writer.writerow(
                [
                    str(claim.claim_id),
                    claim.status_id,
                    claim.submission_date.strftime("%Y-%m-%d %H:%M:%S"),
                    firm_name,
                    firm_code,
                    proceeding.proceeding_id,
                    proceeding.matter_type,
                ]
            )

        return output.getvalue()

    def _build_application_lookup(self, claims: list[Claim]) -> dict[int, Application]:
        lookup: dict[int, Application] = {}

        for claim in claims:
            application = self.application_lookup_port.get_application_by_laa_reference(
                str(claim.laa_reference)
            )
            if application is None or application.provider is None:
                raise ReportGenerationError(
                    f"Application not found for claim {claim.claim_id}"
                )

            lookup[claim.claim_id] = application

        return lookup

    def _build_firm_name_lookup(
        self, applications: list[Application]
    ) -> dict[str, str]:
        firm_codes = list({app.provider.firm_code for app in applications})
        firms = self.provider_details_port.get_firms_by_ids(firm_codes)
        return {firm["firmNumber"]: firm["firmName"] for firm in firms}
