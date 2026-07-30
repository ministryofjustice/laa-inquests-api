from app.models.application.certificate import ApplicationCertificate
from app.models.application.enums import MeritsDecision
from app.ports.get_application_port import GetApplicationPort
from app.use_cases.create_certificate_context import CreateCertificateContextUseCase
from app.use_cases.exceptions import (
    ApplicationNotFoundError,
    ApplicationNotGrantedError,
    ProceedingNotFoundError,
)


class RetrieveCertificateUseCase:
    def __init__(
        self,
        get_application_port: GetApplicationPort,
        create_certificate_context_use_case: CreateCertificateContextUseCase,
    ) -> None:
        self.get_application_port = get_application_port
        self.create_certificate_context_use_case = create_certificate_context_use_case

    def execute(self, laa_reference: str) -> ApplicationCertificate:
        application = self.get_application_port.get_application_by_laa_reference(
            laa_reference
        )
        if application is None:
            raise ApplicationNotFoundError(f"Application {laa_reference} not found")

        if application.overall_decision != MeritsDecision.GRANTED:
            raise ApplicationNotGrantedError(
                f"Application {laa_reference} is not granted"
            )

        if not application.proceeding:
            raise ProceedingNotFoundError(
                f"No proceeding found for application {laa_reference}"
            )

        proceeding = application.proceeding
        return self.create_certificate_context_use_case.populate_certificate_context(
            application,
            proceeding,
        )
