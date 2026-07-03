import logging

from app.models.application.enums import MeritsDecision
from app.models.application.index import MeritsDecisionUpdateRefuse
from app.ports.gov_notify_port import GovNotifyPort
from app.ports.commit_decision_port import ApplicationDecisionPort
from app.use_cases.exceptions import ApplicationNotFoundError, ProceedingsNotFoundError

logger = logging.getLogger(__name__)


class RefuseDecisionUseCase:
    def __init__(
        self,
        application_decision_port: ApplicationDecisionPort,
        gov_notify_port: GovNotifyPort,
    ) -> None:
        self.application_decision_port = application_decision_port
        self.gov_notify_port = gov_notify_port

    def execute(self, laa_reference: str, request: MeritsDecisionUpdateRefuse) -> None:
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
        proceeding.merits_decision = MeritsDecision.REFUSED
        proceeding.reason_for_refusal = request.reason_for_refusal.value
        proceeding.justification = request.justification

        self.application_decision_port.commit_decision(application, proceeding)

        try:
            self.gov_notify_port.send_application_refused_decision_email(
                application,
                proceeding,
                application.provider.email_address,
            )
        except Exception:
            logger.warning(
                "Failed to send refusal email for application %s",
                application.laa_reference,
                exc_info=True,
            )
