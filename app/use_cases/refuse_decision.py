import logging

from app.contexts.user import get_entra_user_name
from app.logging_utils import build_log_extra
from app.models.application.enums import MeritsDecision
from app.models.application.index import RefuseApplicationUpdate
from app.models.history.enums import ActorType, HistoryEventReference
from app.models.notifications.enums import NotificationType
from app.ports.create_history_event_port import CreateHistoryEventPort
from app.ports.gov_notify_port import GovNotifyPort
from app.ports.update_decision_port import ApplicationDecisionPort
from app.use_cases.exceptions import (
    ApplicationNotFoundError,
    RefuseDecisionError,
)

logger = logging.getLogger(__name__)


class RefuseDecisionUseCase:
    def __init__(
        self,
        application_decision_port: ApplicationDecisionPort,
        gov_notify_port: GovNotifyPort,
        create_history_event_port: CreateHistoryEventPort,
    ) -> None:
        self.application_decision_port = application_decision_port
        self.gov_notify_port = gov_notify_port
        self.create_history_event_port = create_history_event_port

    def execute(self, laa_reference: str, request: RefuseApplicationUpdate) -> None:
        application = self.application_decision_port.get_application_by_laa_reference(
            laa_reference
        )
        if application is None:
            raise ApplicationNotFoundError(f"Application {laa_reference} not found")

        proceeding = application.proceeding
        proceeding.merits_decision = MeritsDecision.REFUSED
        proceeding.reason_for_refusal = request.reason_for_refusal.value
        proceeding.justification = request.justification

        self.application_decision_port.update_decision(proceeding)

        self.create_history_event_port.create_history_event(
            event_reference=HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED,
            actor=get_entra_user_name(),
            actor_type=ActorType.CASEWORKER,
            application_id=application.application_id,
            event_data={
                "merits_decision": "Refused",
                "refusal_reason": request.reason_for_refusal.value,
                "refusal_justification": request.justification,
            },
        )

        try:
            self.gov_notify_port.send_application_refused_decision_email(
                application,
                proceeding,
                application.provider.email_address,
            )
            self.create_history_event_port.create_history_event(
                event_reference=HistoryEventReference.APPLICATION_REFUSED,
                actor="System",
                actor_type=ActorType.SYSTEM,
                application_id=application.application_id,
                event_data={
                    "recipient": application.provider.email_address,
                    "channel": NotificationType.EMAIL,
                },
            )
            self.application_decision_port.commit()
            self.create_history_event_port.commit()
        except Exception as exception:
            logger.warning(
                "Failed to refuse application",
                extra=build_log_extra(
                    event="refuse_decision_failed",
                    laa_reference=application.laa_reference,
                ),
                exc_info=True,
            )
            self.application_decision_port.rollback()
            self.create_history_event_port.rollback()
            raise RefuseDecisionError("Failed to refuse application.") from exception
