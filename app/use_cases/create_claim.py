import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from app.domain.application import ApplicationDomain
from app.domain.claim import Claim as DomainClaim
from app.domain.claim import ExistingClaimSummary
from app.domain.claim_error import ClaimErrorCode, ClaimValidationError
from app.domain.constants.claim_messages import APPLICATION_NOT_GRANTED_MESSAGE
from app.models.claim.enums import (
    ClaimDecisionStatus,
    ClaimStatus,
    ClaimType,
    POAType,
    ReasonCode,
)
from app.models.claim.index import Claim
from app.models.history.enums import ActorType, HistoryEventReference
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.claim.create_claim_decision_port import CreateClaimDecisionPort
from app.ports.claim.create_claim_port import CreateClaimPort
from app.ports.claim.create_decision_reason_port import CreateDecisionReasonPort
from app.ports.claim.get_claims_for_application_port import GetClaimsForApplicationPort
from app.ports.claim.update_claim_status_port import (
    UpdateClaimStatusPort,
)
from app.ports.create_history_event_port import CreateHistoryEventPort
from app.ports.gov_notify_port import GovNotifyPort
from app.use_cases.exceptions import ApplicationNotFoundError, InvalidClaimError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CreateClaimCommand:
    laa_reference: str
    firm_code: str
    claim_type: ClaimType
    poa_type: POAType | None
    net: Decimal | None
    gross: Decimal | None
    vat_zero_total: Decimal | None
    claimant_id: str | None
    claim_evidence_ids: list[uuid.UUID]


@dataclass(frozen=True)
class CreateClaimResult:
    claim: Claim
    rejection_reasons: list[ReasonCode] | None = None


class CreateClaimUseCase:
    def __init__(
        self,
        create_claim_port: CreateClaimPort,
        application_lookup_port: ApplicationLookupPort,
        get_claims_for_application_port: GetClaimsForApplicationPort,
        create_history_event_port: CreateHistoryEventPort | None = None,
        gov_notify_port: GovNotifyPort | None = None,
        create_claim_decision_port: CreateClaimDecisionPort | None = None,
        create_decision_reason_port: CreateDecisionReasonPort | None = None,
        update_claim_status_port: UpdateClaimStatusPort | None = None,
    ) -> None:
        self.create_claim_port = create_claim_port
        self.application_lookup_port = application_lookup_port
        self.get_claims_for_application_port = get_claims_for_application_port
        self.create_history_event_port = create_history_event_port
        self.gov_notify_port = gov_notify_port
        self.create_claim_decision_port = create_claim_decision_port
        self.create_decision_reason_port = create_decision_reason_port
        self.update_claim_status_port = update_claim_status_port

    def execute(self, command: CreateClaimCommand) -> CreateClaimResult:
        if not command.claim_evidence_ids:
            raise InvalidClaimError(
                code=ClaimErrorCode.MISSING_CLAIM_EVIDENCE,
                message="Claim evidence is required",
            )

        application = self.application_lookup_port.get_application_by_laa_reference(
            command.laa_reference
        )
        if application is None or application.provider.firm_code != command.firm_code:
            raise ApplicationNotFoundError(command.laa_reference)

        domain_application = ApplicationDomain(
            overall_decision=application.overall_decision
        )
        if not domain_application.is_granted:
            raise InvalidClaimError(
                code=ClaimErrorCode.APPLICATION_NOT_GRANTED,
                message=APPLICATION_NOT_GRANTED_MESSAGE,
            )

        try:
            validated_claim = DomainClaim(
                claim_type=command.claim_type,
                poa_type=command.poa_type,
                net=command.net,
                gross=command.gross,
                vat_zero_total=command.vat_zero_total,
            )
            validated_claim.validate_total_claim_cost()
        except ClaimValidationError as e:
            raise InvalidClaimError(code=e.code, message=e.message) from e

        existing_claims = (
            self.get_claims_for_application_port.get_claims_by_laa_reference(
                command.laa_reference
            )
        )

        claim = self.create_claim_port.create_claim(
            laa_reference=command.laa_reference,
            claim=validated_claim,
            claimant_id=command.claimant_id,
        )
        self.create_claim_port.link_evidence_to_claim(
            claim.claim_id, command.claim_evidence_ids
        )
        self.create_claim_port.commit()

        if self.create_history_event_port is not None:
            self.create_history_event_port.create_history_event(
                event_reference=HistoryEventReference.CLAIM_SUBMITTED,
                actor=command.claimant_id or application.provider.email_address,
                actor_type=ActorType.PROVIDER,
                laa_reference=command.laa_reference,
                event_data={"claim_type": command.claim_type.value},
            )
            self.create_history_event_port.commit()

        if application is not None and self.gov_notify_port is not None:
            try:
                self.gov_notify_port.send_claim_submit_confirmation_email(
                    claim=claim,
                    application=application,
                    recipient_email=application.provider.email_address,
                )
            except Exception:
                logger.warning(
                    "Failed to send claim submission email for claim %s",
                    claim.claim_id,
                    exc_info=True,
                )

        rejection_reasons: list[ReasonCode] | None = None

        if application is not None:
            reference_date = datetime.now(UTC)
            existing_summaries = [
                ExistingClaimSummary(
                    status=c.status_id,
                    poa_type=c.poa_type_id,
                    submission_date=c.submission_date,
                    net=c.total_profit_cost_net,
                    gross=c.total_profit_cost_gross,
                    vat_zero_total=c.total_profit_cost_vat_zero,
                )
                for c in existing_claims
            ]
            rejection = validated_claim.should_auto_reject(
                application, existing_summaries, reference_date
            )

            if (
                rejection.is_rejected
                and self.create_claim_decision_port is not None
                and self.create_decision_reason_port is not None
                and self.update_claim_status_port is not None
            ):
                try:
                    claim_decision = (
                        self.create_claim_decision_port.create_claim_decision(
                            claim_id=claim.claim_id,
                            decision_status=ClaimDecisionStatus.REJECT,
                        )
                    )
                    rejection_reasons = [
                        ReasonCode(reason.value) for reason in rejection.reasons
                    ]
                    for reason_code in rejection_reasons:
                        self.create_decision_reason_port.create_decision_reason(
                            claim_decision_id=claim_decision.claim_decision_id,
                            reason_code=reason_code,
                            justification=None,
                        )
                    self.update_claim_status_port.update_claim_status(
                        claim_id=claim.claim_id,
                        status=ClaimStatus.REJECTED,
                    )
                    self.create_claim_port.commit()
                    claim.status_id = ClaimStatus.REJECTED
                except Exception:
                    self.create_claim_port.rollback()
                    claim.status_id = ClaimStatus.SUBMITTED
                    rejection_reasons = None
                    logger.warning(
                        "Failed to persist claim auto-rejection for claim %s",
                        claim.claim_id,
                        exc_info=True,
                    )

            if (
                not rejection.is_rejected
                and validated_claim.is_eligible_for_auto_approval(application)
                and self.create_claim_decision_port is not None
                and self.update_claim_status_port is not None
            ):
                try:
                    self.create_claim_decision_port.create_claim_decision(
                        claim_id=claim.claim_id,
                        decision_status=ClaimDecisionStatus.PAY_IN_FULL,
                    )
                    self.update_claim_status_port.update_claim_status(
                        claim_id=claim.claim_id,
                        status=ClaimStatus.PAY_IN_FULL,
                    )
                    self.create_claim_port.commit()
                    claim.status_id = ClaimStatus.PAY_IN_FULL
                except Exception:
                    self.create_claim_port.rollback()
                    claim.status_id = ClaimStatus.SUBMITTED
                    logger.warning(
                        "Failed to persist claim auto-approval for claim %s",
                        claim.claim_id,
                        exc_info=True,
                    )

        return CreateClaimResult(claim=claim, rejection_reasons=rejection_reasons)
