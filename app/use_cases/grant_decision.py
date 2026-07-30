import logging
from datetime import UTC, datetime

from app.models.application.enums import MeritsDecision
from app.models.application.index import GrantApplicationUpdate
from app.ports.update_decision_port import ApplicationDecisionPort
from app.use_cases.create_certificate_context import CreateCertificateContextUseCase
from app.use_cases.exceptions import ApplicationNotFoundError, ProceedingsNotFoundError
from app.use_cases.send_grant_email import SendGrantEmailUseCase
from app.use_cases.send_grant_letter import SendGrantLetterUseCase

logger = logging.getLogger(__name__)


class GrantDecisionUseCase:
    def __init__(
        self,
        application_decision_port: ApplicationDecisionPort,
        create_certificate_context_use_case: CreateCertificateContextUseCase,
        send_grant_email_use_case: SendGrantEmailUseCase,
        send_grant_letter_use_case: SendGrantLetterUseCase,
    ) -> None:
        self.application_decision_port = application_decision_port
        self.create_certificate_context_use_case = create_certificate_context_use_case
        self.send_grant_email_use_case = send_grant_email_use_case
        self.send_grant_letter_use_case = send_grant_letter_use_case

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
            certificate_context = (
                self.create_certificate_context_use_case.prepare_context_for_display(
                    certificate_context
                )
            )

            self.send_grant_email_use_case.execute(
                application, proceeding, certificate_context
            )

            self.send_grant_letter_use_case.execute(certificate_context)

            self.application_decision_port.commit()
        except Exception as exception:
            logger.warning(
                "Failed to send grant email for application %s",
                application.laa_reference,
                exc_info=True,
            )
            self.application_decision_port.rollback()
            raise Exception("Failed to grant application.") from exception
