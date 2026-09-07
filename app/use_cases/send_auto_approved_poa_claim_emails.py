"""Use case for sending grant emails for POA claims auto-approved in the last 24 hours."""

import logging
from datetime import UTC, datetime, timedelta

from app.models.claim.index import Claim
from app.models.history.enums import ActorType, HistoryEventReference
from app.models.history.index import HistoryEvent
from app.ports.claim.list_auto_approved_poa_claims_port import (
    ListAutoApprovedPoaClaimsPort,
)
from app.ports.create_history_event_port import CreateHistoryEventPort
from app.ports.get_application_history_port import GetApplicationHistoryPort
from app.ports.gov_notify_port import GovNotifyPort
from app.ports.provider_details_port import ProviderDetailsPort

logger = logging.getLogger(__name__)

WINDOW = timedelta(hours=24)


class SendAutoApprovedPoaClaimEmailsUseCase:
    """Send the deferred grant email for each POA claim auto-approved in the last 24 hours."""

    def __init__(
        self,
        list_auto_approved_poa_claims_port: ListAutoApprovedPoaClaimsPort,
        get_application_history_port: GetApplicationHistoryPort,
        create_history_event_port: CreateHistoryEventPort,
        provider_details_port: ProviderDetailsPort,
        gov_notify_port: GovNotifyPort,
    ) -> None:
        self.list_auto_approved_poa_claims_port = list_auto_approved_poa_claims_port
        self.get_application_history_port = get_application_history_port
        self.create_history_event_port = create_history_event_port
        self.provider_details_port = provider_details_port
        self.gov_notify_port = gov_notify_port

    def execute(self, now: datetime | None = None) -> None:
        end_utc = now or datetime.now(UTC)
        start_utc = end_utc - WINDOW
        claims = self.list_auto_approved_poa_claims_port.list_auto_approved_poa_claims(
            start_utc, end_utc
        )

        for claim in claims:
            try:
                self._process_claim(claim)
            except Exception:
                logger.warning(
                    "Failed to send auto-approved POA grant email for claim %s",
                    claim.claim_id,
                    exc_info=True,
                )

    def _process_claim(self, claim: Claim) -> None:
        application = claim.application
        history = self.get_application_history_port.get_application_history(
            application.application_id
        )

        if not self._has_event(
            history, HistoryEventReference.POA_AUTO_APPROVED, claim.claim_id
        ):
            return
        if self._has_event(
            history, HistoryEventReference.POA_AUTO_APPROVE_EMAIL_SENT, claim.claim_id
        ):
            return

        firm_name = self.provider_details_port.get_firm_name(
            application.provider.firm_code
        )
        self.gov_notify_port.send_claim_granted_decision_email(
            claim=claim,
            application=application,
            recipient_email=application.provider.email_address,
            firm_name=firm_name,
        )
        self.create_history_event_port.create_history_event(
            event_reference=HistoryEventReference.POA_AUTO_APPROVE_EMAIL_SENT,
            actor=ActorType.SYSTEM,
            actor_type=ActorType.SYSTEM,
            application_id=application.application_id,
            event_data={"claim_reference": claim.claim_id},
        )
        self.create_history_event_port.commit()

    @staticmethod
    def _has_event(
        history: list[HistoryEvent],
        reference: HistoryEventReference,
        claim_id: int,
    ) -> bool:
        return any(
            event.event_reference == reference
            and (event.event_data or {}).get("claim_reference") == claim_id
            for event in history
        )
