import logging

from app.logging_utils import build_log_extra
from app.models.application.index import (
    Application,
    ApplicationResponse,
    PotentialDuplicateApplicationResponse,
    ProviderResponse,
)
from app.ports.get_application_port import GetApplicationPort
from app.ports.get_potential_duplicate_applications_port import (
    GetPotentialDuplicateApplicationsPort,
)
from app.ports.provider_details_port import ProviderDetailsPort
from app.use_cases.exceptions import ApplicationNotFoundError

logger = logging.getLogger(__name__)


class GetApplicationUseCase:
    def __init__(
        self,
        get_application_port: GetApplicationPort,
        provider_details_port: ProviderDetailsPort,
        get_potential_duplicate_applications_port: GetPotentialDuplicateApplicationsPort,
    ) -> None:
        self.get_application_port = get_application_port
        self.provider_details_port = provider_details_port
        self.get_potential_duplicate_applications_port = (
            get_potential_duplicate_applications_port
        )

    def execute(self, laa_reference: str) -> ApplicationResponse:
        application = self.get_application_port.get_application_by_laa_reference(
            laa_reference
        )
        if application is None:
            logger.error(
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

        duplicate_applications_ids = self.get_potential_duplicate_applications_port.get_potential_duplicate_application_ids(
            application.application_id
        )
        duplicate_applications = self.get_potential_duplicate_applications_port.get_duplicate_applications_by_ids(
            duplicate_applications_ids
        )
        response.potential_duplicate_applications = (
            self.prepare_duplicate_applications_response(duplicate_applications)
        )

        logger.info(
            "Application retrieved",
            extra=build_log_extra(
                event="application_retrieved_success",
                laa_reference=laa_reference,
            ),
        )
        return response

    @staticmethod
    def prepare_duplicate_applications_response(
        duplicate_applications: list[Application],
    ) -> list[PotentialDuplicateApplicationResponse] | None:
        if not duplicate_applications:
            return None

        return [
            PotentialDuplicateApplicationResponse(
                laa_reference=duplicate.laa_reference,
                status=duplicate.overall_decision,
            )
            for duplicate in duplicate_applications
        ]
