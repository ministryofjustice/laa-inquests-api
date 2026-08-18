import logging
from dataclasses import dataclass

from app.models.claim.enums import ClaimDecisionStatus, ClaimStatus, ReasonCode
from app.models.history.enums import ActorType, HistoryEventReference
from app.models.notifications.enums import NotificationType
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.claim.create_claim_decision_port import CreateClaimDecisionPort
from app.ports.claim.create_decision_reason_port import CreateDecisionReasonPort
from app.ports.claim.get_claim_by_id_port import GetClaimByIdPort
from app.ports.claim.update_claim_status_port import UpdateClaimStatusPort
from app.ports.create_history_event_port import CreateHistoryEventPort
from app.use_cases.exceptions import ApplicationNotFoundError, ClaimNotFoundError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RejectClaimCommand:
    laa_reference: str
    claim_id: int
    justification: str


class RejectClaimUseCase:
    def __init__(
        self,
        application_lookup_port: ApplicationLookupPort,
        get_claim_by_id_port: GetClaimByIdPort,
        create_claim_decision_port: CreateClaimDecisionPort,
        create_decision_reason_port: CreateDecisionReasonPort,
        update_claim_status_port: UpdateClaimStatusPort,
        create_history_event_port: CreateHistoryEventPort,
    ) -> None:
        self.application_lookup_port = application_lookup_port
        self.get_claim_by_id_port = get_claim_by_id_port
        self.create_claim_decision_port = create_claim_decision_port
        self.create_decision_reason_port = create_decision_reason_port
        self.update_claim_status_port = update_claim_status_port
        self.create_history_event_port = create_history_event_port

    def execute(self, command: RejectClaimCommand, caseworker_name: str) -> None:
        application = self.application_lookup_port.get_application_by_laa_reference(
            command.laa_reference
        )
        if application is None:
            raise ApplicationNotFoundError(command.laa_reference)

        claim = self.get_claim_by_id_port.get_claim_by_id(command.claim_id)
        if claim is None or claim.laa_reference != application.laa_reference:
            raise ClaimNotFoundError(command.claim_id)

        try:
            claim_decision = self.create_claim_decision_port.create_claim_decision(
                claim_id=command.claim_id,
                decision_status=ClaimDecisionStatus.REJECT,
            )
            self.create_decision_reason_port.create_decision_reason(
                claim_decision_id=claim_decision.claim_decision_id,
                reason_code=ReasonCode.MANUAL_REJECTION,
                justification=command.justification,
            )
            self.update_claim_status_port.update_claim_status(
                claim_id=command.claim_id,
                status=ClaimStatus.REJECTED,
            )

            self.create_history_event_port.create_history_event(
                event_reference=HistoryEventReference.CLAIM_ASSESSMENT_COMPLETED,
                actor=caseworker_name,
                actor_type=ActorType.CASEWORKER,
                laa_reference=application.laa_reference,
                event_data={
                    "claim_type": claim.claim_type_id,
                    "claim_decision": ClaimStatus.REJECTED,
                    "decision_justification": command.justification,
                },
            )

            (
                self.create_history_event_port.create_history_event(
                    event_reference=HistoryEventReference.CLAIM_REJECTED_EMAIL,
                    actor=ActorType.SYSTEM,
                    actor_type=ActorType.SYSTEM,
                    laa_reference=command.laa_reference,
                    event_data={
                        "recipient": application.provider.email_address,
                        "channel": NotificationType.EMAIL,
                    },
                ),
            )

            self.update_claim_status_port.commit()
        except Exception:
            self.update_claim_status_port.rollback()
            raise
