from sqlmodel import Session

from app.models.application.index import (
    Application,
    ApplicationResponse,
    ProviderResponse,
)
from app.ports.provider_details_port import ProviderDetailsPort
from app.use_cases.exceptions import ApplicationNotFoundError


class ReadApplicationUseCase:
    def __init__(
        self, session: Session, provider_details_port: ProviderDetailsPort
    ) -> None:
        self.session = session
        self.provider_details_port = provider_details_port

    def execute(self, laa_reference: str) -> ApplicationResponse:
        application = self.session.get(Application, int(laa_reference))
        if application is None:
            raise ApplicationNotFoundError(f"Application {laa_reference} not found")
        firm_name = self.provider_details_port.get_firm_name(
            application.provider.firm_code
        )
        email_address = self.provider_details_port.get_office_email(
            application.provider.firm_code, application.provider.office_id
        )
        provider_response = ProviderResponse(
            firm_name=firm_name,
            account_number=application.provider.office_id,
            email_address=email_address,
        )
        response = ApplicationResponse.model_validate(application)
        response.provider = provider_response
        return response
