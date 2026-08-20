import logging

from app.logging_utils import build_log_extra
from app.models.application.index import ApplicationResponse, ProviderResponse
from app.ports.get_application_port import GetApplicationPort
from app.ports.provider_details_port import ProviderDetailsPort
from app.use_cases.exceptions import ApplicationNotFoundError

logger = logging.getLogger(__name__)


class GetApplicationUseCase:
    def __init__(
        self,
        get_application_port: GetApplicationPort,
        provider_details_port: ProviderDetailsPort,
    ) -> None:
        self.get_application_port = get_application_port
        self.provider_details_port = provider_details_port

    def execute(self, laa_reference: str) -> ApplicationResponse:
        application = self.get_application_port.get_application_by_laa_reference(
            laa_reference
        )
        if application is None:
            logger.warning(
                "Application retrieval failed",
                extra=build_log_extra(
                    event="application_retrieved_failed",
                    laa_reference=laa_reference,
                ),
            )
            raise ApplicationNotFoundError(f"Application {laa_reference} not found")

        firm_name = self.provider_details_port.get_firm_name(
            application.provider.firm_code
        )
        provider_response = ProviderResponse(
            firm_name=firm_name,
            account_number=application.provider.office_id,
            email_address=application.provider.email_address,
        )
        if application.client.correspondence_address_source == "USE_PROVIDER_ADDRESS":
            office_address = self.provider_details_port.get_office_address(
                application.provider.office_id
            )
            if office_address:
                application.client.correspondence_address = office_address

        response = ApplicationResponse.model_validate(application)
        response.provider = provider_response
        logger.info(
            "Application retrieved",
            extra=build_log_extra(
                event="application_retrieved_success",
                laa_reference=laa_reference,
            ),
        )
        return response
