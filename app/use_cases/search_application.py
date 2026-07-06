from app.models.application.index import ApplicationSearchResponse
from app.ports.search_application_port import SearchApplicationPort
from app.ports.provider_details_port import ProviderDetailsPort


class SearchApplicationUseCase:
    def __init__(
        self,
        search_application_port: SearchApplicationPort,
        provider_details_port: ProviderDetailsPort,
    ) -> None:
        self.search_application_port = search_application_port
        self.provider_details_port = provider_details_port

    def execute(self, laa_reference: str) -> list[ApplicationSearchResponse]:
        normalised_reference = laa_reference.strip()
        matching_applications = self.search_application_port.search_applications(
            normalised_reference
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
