from datetime import datetime, UTC
import logging
from app.use_cases.create_certificate_context import CreateCertificateContextUseCase
from app.models.application.enums import MeritsDecision
from app.models.application.index import GrantApplicationUpdate
from app.ports.gov_notify_port import GovNotifyPort
from app.ports.update_decision_port import ApplicationDecisionPort
from app.ports.pdf_generation_port import PdfGenerationPort
from app.use_cases.exceptions import ApplicationNotFoundError, ProceedingsNotFoundError

logger = logging.getLogger(__name__)


class GrantDecisionUseCase:
    def __init__(
        self,
        application_decision_port: ApplicationDecisionPort,
        gov_notify_port: GovNotifyPort,
        pdf_generation_port: PdfGenerationPort,
        create_certificate_context_use_case: CreateCertificateContextUseCase,
    ) -> None:
        self.application_decision_port = application_decision_port
        self.gov_notify_port = gov_notify_port
        self.pdf_generation_port = pdf_generation_port
        self.create_certificate_context_use_case = create_certificate_context_use_case

    def execute(self, laa_reference: str, request: GrantApplicationUpdate) -> None:
        application = self.application_decision_port.get_application_by_laa_reference(
            laa_reference
        )
        if application is None:
            raise ApplicationNotFoundError(f"Application {laa_reference} not found")

        if not application.proceedings:
            raise ProceedingsNotFoundError(
                f"No proceedings found for application {laa_reference}"
            )

        proceeding = application.proceedings[0]
        proceeding.merits_decision = MeritsDecision.GRANTED
        proceeding.reason_for_refusal = None
        proceeding.justification = None
        proceeding.certificate_start_date = request.certificate_start_date
        proceeding.certificate_issue_date = datetime.now(UTC).date()

        self.application_decision_port.update_decision(proceeding)

        try:
            certificate_context = (
                self.create_certificate_context_use_case.populate_certificate_context(
                    application, proceeding
                )
            )
            certificate_pdf = self.pdf_generation_port.generate_pdf(
                "certificate.html", certificate_context
            )

            self.gov_notify_port.send_application_granted_decision_email(
                application,
                proceeding,
                application.provider.email_address,
                certificate_pdf,
            )
            self.application_decision_port.commit()
        except Exception as exception:
            logger.warning(
                "Failed to send grant email for application %s",
                application.laa_reference,
                exc_info=True,
            )
            self.application_decision_port.rollback()
            raise Exception("Failed to grant application.") from exception
