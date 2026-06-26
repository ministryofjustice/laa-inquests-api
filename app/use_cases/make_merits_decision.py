import logging

from app.models.application.enums import MeritsDecision
from app.models.application.index import MeritsDecisionUpdateRefuse
from app.ports.gov_notify_port import GovNotifyPort
from app.ports.make_merits_decision_port import MakeMeritsDecisionPort
from app.use_cases.exceptions import ApplicationNotFoundError, ProceedingsNotFoundError

logger = logging.getLogger(__name__)


class MakeMeritsDecisionUseCase:
    def __init__(
        self,
        make_merits_decision_port: MakeMeritsDecisionPort,
        gov_notify_port: GovNotifyPort,
    ) -> None:
        self.make_merits_decision_port = make_merits_decision_port
        self.gov_notify_port = gov_notify_port

    def execute(self, laa_reference: str, request: MeritsDecisionUpdateRefuse) -> None:
        application = self.make_merits_decision_port.get_application_by_laa_reference(
            laa_reference
        )
        if application is None:
            raise ApplicationNotFoundError(f"Application {laa_reference} not found")

        if not application.proceedings:
            raise ProceedingsNotFoundError(
                f"No proceedings found for application {laa_reference}"
            )

        proceeding = application.proceedings[0]
        proceeding.merits_decision = request.merits_decision
        proceeding.reason_for_refusal = (
            request.reason_for_refusal.value if request.reason_for_refusal else None
        )
        proceeding.justification = request.justification
        application.overall_decision = request.merits_decision

        self.make_merits_decision_port.persist_merits_decision(application, proceeding)

        if request.merits_decision == MeritsDecision.REFUSED:
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
