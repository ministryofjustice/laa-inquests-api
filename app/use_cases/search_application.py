import logging

from app.logging_utils import build_log_extra
from app.models.application.enums import MeritsDecision
from app.models.application.index import ApplicationSearchResponse
from app.ports.provider_details_port import ProviderDetailsPort
from app.ports.search_application_port import SearchApplicationPort

logger = logging.getLogger(__name__)


class SearchApplicationUseCase:
    def __init__(
        self,
        search_application_port: SearchApplicationPort,
        provider_details_port: ProviderDetailsPort,
    ) -> None:
        self.search_application_port = search_application_port
        self.provider_details_port = provider_details_port

    def execute(
        self,
        laa_reference: str,
        firm_code: str,
        merits_decision: MeritsDecision | None = None,
    ) -> list[ApplicationSearchResponse]:
        try:
            normalised_reference = laa_reference.strip()
            matching_applications = self.search_application_port.search_applications(
                normalised_reference, firm_code, merits_decision
            )
            if not matching_applications:
                return []

            firm_name = self.provider_details_port.get_firm_name(
                matching_applications[0].provider.firm_code
            )

            return [
                ApplicationSearchResponse(
                    laa_reference=application.laa_reference,
                    client_first_name=application.client.client_first_name,
                    client_last_name=application.client.client_last_name,
                    client_date_of_birth=application.client.date_of_birth,
                    date_submitted=application.created_at,
                    firm_name=firm_name,
                    firm_number=application.provider.firm_code,
                    overall_decision=application.overall_decision,
                )
                for application in matching_applications
            ]
        except Exception:
            logger.exception(
                "Search application failed",
                extra=build_log_extra(
                    event="search_application_failed",
                    laa_reference=laa_reference,
                    firm_code=firm_code,
                ),
            )
            raise
