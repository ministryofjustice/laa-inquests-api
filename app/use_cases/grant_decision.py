import logging
from datetime import UTC, datetime

from app.contexts.user import get_entra_user_name
from app.logging_utils import build_log_extra
from app.models.application.enums import MeritsDecision
from app.models.application.index import GrantApplicationUpdate
from app.models.history.enums import ActorType, HistoryEventReference
from app.models.notifications.enums import NotificationType
from app.ports.create_history_event_port import CreateHistoryEventPort
from app.ports.update_decision_port import ApplicationDecisionPort
from app.use_cases.create_certificate_context import CreateCertificateContextUseCase
from app.use_cases.exceptions import (
    ApplicationNotFoundError,
    GrantDecisionError,
)
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
        create_history_event_port: CreateHistoryEventPort,
    ) -> None:
        self.application_decision_port = application_decision_port
        self.create_certificate_context_use_case = create_certificate_context_use_case
        self.send_grant_email_use_case = send_grant_email_use_case
        self.send_grant_letter_use_case = send_grant_letter_use_case
        self.create_history_event_port = create_history_event_port

    def execute(self, laa_reference: str, request: GrantApplicationUpdate) -> None:
        application = self.application_decision_port.get_application_by_laa_reference(
            laa_reference
        )
        if application is None:
            raise ApplicationNotFoundError(f"Application {laa_reference} not found")

        proceeding = application.proceeding
        proceeding.merits_decision = MeritsDecision.GRANTED
        proceeding.reason_for_refusal = None
        proceeding.justification = None
        proceeding.substantive_cost_limitation_effective_date = (
            request.certificate_start_date
        )
        proceeding.certificate_start_date = request.certificate_start_date
        proceeding.certificate_issue_date = datetime.now(UTC).date()

        self.application_decision_port.update_decision(proceeding)
        self.create_history_event_port.create_history_event(
            event_reference=HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED,
            actor=get_entra_user_name(),
            actor_type=ActorType.CASEWORKER,
            application_id=application.application_id,
            event_data={"merits_decision": "Granted"},
        )

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

            self.create_history_event_port.create_history_event(
                event_reference=HistoryEventReference.CERTIFICATE_CREATED,
                actor=get_entra_user_name(),
                actor_type=ActorType.CASEWORKER,
                application_id=application.application_id,
                event_data={
                    "laa_reference": application.laa_reference,
                },
            )

            self.create_history_event_port.create_history_event(
                event_reference=HistoryEventReference.APPLICATION_GRANTED_EMAIL,
                actor="System",
                actor_type=ActorType.SYSTEM,
                application_id=application.application_id,
                event_data={
                    "recipient": application.provider.email_address,
                    "channel": NotificationType.EMAIL,
                },
            )

            self.send_grant_letter_use_case.execute(certificate_context)

            self.create_history_event_port.create_history_event(
                event_reference=HistoryEventReference.APPLICATION_GRANTED_LETTER,
                actor="System",
                actor_type=ActorType.SYSTEM,
                application_id=application.application_id,
                event_data={
                    "recipient": certificate_context.client_address.model_dump(),
                    "channel": NotificationType.LETTER,
                },
            )

            self.application_decision_port.commit()
            self.create_history_event_port.commit()
        except Exception as exception:
            logger.warning(
                "Failed to grant application",
                extra=build_log_extra(
                    event="grant_decision_failed",
                    laa_reference=application.application_id,
                ),
                exc_info=True,
            )
            self.application_decision_port.rollback()
            self.create_history_event_port.rollback()
            raise GrantDecisionError("Failed to grant application.") from exception
