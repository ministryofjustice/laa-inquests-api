import logging

from app.logging_utils import build_log_extra
from app.models.application.certificate import ApplicationCertificate
from app.models.application.enums import MeritsDecision
from app.ports.get_application_port import GetApplicationPort
from app.use_cases.create_certificate_context import CreateCertificateContextUseCase
from app.use_cases.exceptions import (
    ApplicationNotFoundError,
    ApplicationNotGrantedError,
)

logger = logging.getLogger(__name__)


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
            logger.warning(
                "Retrieve certificate failed: application not found",
                extra=build_log_extra(
                    event="certificate_retrieval_failed",
                    laa_reference=laa_reference,
                ),
            )
            raise ApplicationNotFoundError(f"Application {laa_reference} not found")

        if application.overall_decision != MeritsDecision.GRANTED:
            logger.warning(
                "Retrieve certificate failed: application not granted",
                extra=build_log_extra(
                    event="certificate_retrieval_failed",
                    laa_reference=application.laa_reference,
                ),
            )
            raise ApplicationNotGrantedError(
                f"Application {laa_reference} is not granted"
            )

        proceeding = application.proceeding
        certificate = (
            self.create_certificate_context_use_case.populate_certificate_context(
                application,
                proceeding,
            )
        )
        logger.info(
            "Certificate retrieved",
            extra=build_log_extra(
                event="certificate_retrieved",
                laa_reference=application.laa_reference,
            ),
        )
        return certificate
