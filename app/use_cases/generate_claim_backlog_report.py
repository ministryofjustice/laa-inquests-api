import csv
import io

from app.domain.constants.report_csv_headers import CLAIMS_BACKLOG_REPORT_HEADERS
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
        office_code_lookup = self._build_office_code_lookup(claims)
        unique_office_codes = sorted(set(office_code_lookup.values()))
        office_details_lookup = self.provider_details_port.get_offices_by_codes(
            unique_office_codes
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(CLAIMS_BACKLOG_REPORT_HEADERS)

        for claim in claims:
            office_code = office_code_lookup.get(claim.claim_id)
            office = office_details_lookup.get(office_code)

            if office_code is None:
                raise ReportGenerationError(
                    f"Office code not found for claim {claim.claim_id}"
                )
            if office is None:
                raise ReportGenerationError(
                    f"Office details not found for office code {office_code}"
                )

            office_name = office.get("officeName")
            if not office_name:
                raise ReportGenerationError(
                    f"Office name not found for office code {office_code}"
                )

            # TODO: Are these columns even right? Ticket is unclear
            writer.writerow(
                [
                    str(claim.claim_id),
                    claim.status_id,
                    claim.submission_date.strftime("%Y-%m-%d %H:%M:%S"),
                    office_name,
                    office_code,
                    str(claim.total_profit_cost_vat_zero)
                    if claim.total_profit_cost_vat_zero is not None
                    else "",
                    str(claim.total_profit_cost_net)
                    if claim.total_profit_cost_net is not None
                    else "",
                    str(claim.total_profit_cost_gross)
                    if claim.total_profit_cost_gross is not None
                    else "",
                    str(claim.claim_type_id),
                ]
            )

        return output.getvalue()

    # TODO: Too complicated. Fix this later
    def _build_office_code_lookup(self, claims: list[Claim]) -> dict[int, str]:
        lookup: dict[int, str] = {}

        for claim in claims:
            application = self.application_lookup_port.get_application_by_laa_reference(
                str(claim.laa_reference)
            )
            if application is None or application.provider is None:
                raise ReportGenerationError(
                    f"Application not found for claim {claim.claim_id}"
                )

            office_code = application.provider.office_id
            if not office_code:
                raise ReportGenerationError(
                    f"Office code missing for claim {claim.claim_id}"
                )

            lookup[claim.claim_id] = office_code

        return lookup
