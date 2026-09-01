import csv
import io
import logging

from app.domain.constants.report_csv_headers import CLAIMS_BACKLOG_REPORT_HEADERS
from app.logging_utils import build_log_extra
from app.models.application.index import Application
from app.ports.claim_backlog_port import ClaimBacklogPort
from app.ports.provider_details_port import ProviderDetailsPort
from app.use_cases.exceptions import ReportGenerationError

logger = logging.getLogger(__name__)


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
        try:
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
                    logger.info(
                        "Claim backlog report generation failed: firm name missing",
                        extra=build_log_extra(
                            event="claim_backlog_report_generation_failed",
                            firm_code=firm_code,
                            laa_reference=application.laa_reference,
                        ),
                    )
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

            logger.info(
                "Claim backlog report generated",
                extra=build_log_extra(
                    event="claim_backlog_report_generated",
                    claim_count=len(claims),
                ),
            )
            return output.getvalue()
        except Exception:
            logger.warning(
                "Claim backlog report generation failed",
                extra=build_log_extra(
                    event="claim_backlog_report_generation_failed",
                    claim_count=len(claims),
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
