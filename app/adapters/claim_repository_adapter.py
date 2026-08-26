import logging
import uuid
from decimal import Decimal

from sqlmodel import Session, select

from app.domain.claim import Claim as DomainClaim
from app.domain.claim_evidence import ClaimEvidence as DomainClaimEvidence
from app.domain.constants.claims import SUBSTANTIVE_CERTIFICATE_AMOUNT
from app.logging_utils import build_log_extra
from app.models.application.index import Application
from app.models.claim.enums import (
    ClaimDecisionStatus,
    ClaimStatus,
    InquestOutcomeId,
    ReasonCode,
)
from app.models.claim.index import (
    Claim,
    ClaimCostTemplate,
    ClaimDecision,
    ClaimInquestOutcome,
    DecisionReason,
)
from app.models.claim.index import (
    ClaimEvidence as ClaimEvidenceModel,
)
from app.ports.claim.create_claim_decision_port import CreateClaimDecisionPort
from app.ports.claim.create_claim_port import CreateClaimPort
from app.ports.claim.create_decision_reason_port import CreateDecisionReasonPort
from app.ports.claim.delete_claim_evidence_port import DeleteClaimEvidencePort
from app.ports.claim.get_claim_by_id_port import GetClaimByIdPort
from app.ports.claim.get_claim_decision_port import GetClaimDecisionPort
from app.ports.claim.get_claim_evidence_port import GetClaimEvidencePort
from app.ports.claim.get_claims_for_application_port import GetClaimsForApplicationPort
from app.ports.claim.update_claim_status_port import (
    UpdateClaimStatusPort,
)
from app.ports.claim.upload_claim_evidence_port import UploadClaimEvidencePort
from app.ports.claim_backlog_port import ClaimBacklogPort

logger = logging.getLogger(__name__)


class ClaimRepositoryAdapter(
    CreateClaimPort,
    ClaimBacklogPort,
    GetClaimsForApplicationPort,
    GetClaimByIdPort,
    GetClaimDecisionPort,
    CreateClaimDecisionPort,
    CreateDecisionReasonPort,
    UpdateClaimStatusPort,
    UploadClaimEvidencePort,
    GetClaimEvidencePort,
    DeleteClaimEvidencePort,
):
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_claim(
        self,
        laa_reference: str,
        claim: DomainClaim,
        claimant_id: str | None,
        total_funds_remaining_after_claim: Decimal = Decimal(
            SUBSTANTIVE_CERTIFICATE_AMOUNT
        ),
    ) -> Claim:
        new_claim = Claim(
            laa_reference=int(laa_reference),
            claim_type_id=claim.claim_type,
            total_profit_cost_net=claim.net,
            total_profit_cost_gross=claim.gross,
            total_profit_cost_vat_zero=claim.vat_zero_total,
            total_funds_remaining_after_claim=total_funds_remaining_after_claim,
            poa_type_id=claim.poa_type,
            claimant_id=claimant_id,
            has_counsel_been_paid=claim.has_counsel_been_paid,
            has_alternative_funding=claim.has_alternative_funding,
            has_recovery_costs_awarded=claim.has_recovery_costs_awarded,
            financial_recovery_previous_pre_certificate_costs=(
                claim.financial_recovery_previous_pre_certificate_costs
            ),
            financial_recovery_cost=claim.financial_recovery_cost,
            financial_recovery_damages=claim.financial_recovery_damages,
            financial_recovery_interest=claim.financial_recovery_interest,
            paying_party=claim.paying_party,
            number_of_counsel_instructed=claim.number_of_counsel_instructed,
        )
        self.session.add(new_claim)
        self.session.flush()
        self.session.refresh(new_claim)
        logger.info(
            "Claim created in repository",
            extra=build_log_extra(
                event="claim_repository_create_completed",
                laa_reference=laa_reference,
                claim_id=new_claim.claim_id,
            ),
        )
        return new_claim

    def link_evidence_to_claim(
        self,
        claim_id: int,
        evidence_ids: list[uuid.UUID],
    ) -> None:
        for evidence_id in evidence_ids:
            evidence = self.session.get(ClaimEvidenceModel, evidence_id)
            if evidence is not None:
                evidence.claim_id = claim_id
                self.session.add(evidence)
        self.session.flush()
        logger.info(
            "Claim evidence linked in repository",
            extra=build_log_extra(
                event="claim_repository_evidence_link_completed",
                claim_id=claim_id,
                evidence_count=len(evidence_ids),
            ),
        )

    def link_inquest_outcomes_to_claim(
        self,
        claim_id: int,
        inquest_outcomes: list[InquestOutcomeId],
    ) -> None:
        for inquest_outcome in inquest_outcomes:
            self.session.add(
                ClaimInquestOutcome(
                    claim_id=claim_id,
                    inquest_outcome_id=inquest_outcome,
                )
            )
        self.session.flush()
        logger.info(
            "Claim inquest outcomes linked in repository",
            extra=build_log_extra(
                event="claim_repository_inquest_outcome_link_completed",
                claim_id=claim_id,
                inquest_outcome_count=len(inquest_outcomes),
            ),
        )

    def link_cost_template_to_claim(
        self,
        claim_id: int,
        file_id: uuid.UUID,
        file_name: str,
    ) -> None:
        self.session.add(
            ClaimCostTemplate(
                claim_id=claim_id,
                claim_cost_template_file_id=file_id,
                claim_cost_template_file_name=file_name,
            )
        )
        self.session.flush()
        logger.info(
            "Claim cost template linked in repository",
            extra=build_log_extra(
                event="claim_repository_cost_template_link_completed",
                claim_id=claim_id,
            ),
        )

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def get_claims_by_laa_reference(self, laa_reference: str) -> list[Claim]:
        statement = select(Claim).where(Claim.laa_reference == int(laa_reference))
        return list(self.session.exec(statement).all())

    def get_claim_by_id(self, claim_id: int) -> Claim | None:
        return self.session.get(Claim, claim_id)

    def get_claim_decision_by_claim_id(self, claim_id: int) -> ClaimDecision | None:
        statement = (
            select(ClaimDecision)
            .where(ClaimDecision.claim_id == claim_id)
            .order_by(ClaimDecision.claim_decision_id.desc())
        )
        return self.session.exec(statement).first()

    def get_open_claims(self) -> list[Claim]:
        statement = (
            select(Claim)
            .join(Application, Claim.laa_reference == Application.laa_reference)
            .where(Claim.status_id == ClaimStatus.SUBMITTED)
            .order_by(Claim.submission_date.asc())
        )
        return list(self.session.exec(statement).all())

    def create_claim_decision(
        self,
        claim_id: int,
        decision_status: ClaimDecisionStatus,
    ) -> ClaimDecision:
        decision = ClaimDecision(
            claim_id=claim_id,
            decision=decision_status,
        )
        self.session.add(decision)
        self.session.flush()
        self.session.refresh(decision)
        logger.info(
            "Claim decision created in repository",
            extra=build_log_extra(
                event="claim_repository_decision_create_completed",
                claim_id=claim_id,
                decision_status=decision_status,
            ),
        )
        return decision

    def create_decision_reason(
        self,
        claim_decision_id: int,
        reason_code: ReasonCode,
        justification: str | None = None,
    ) -> DecisionReason:
        reason = DecisionReason(
            claim_decision_id=claim_decision_id,
            reason_code=reason_code,
            justification=justification,
        )
        self.session.add(reason)
        self.session.flush()
        self.session.refresh(reason)
        logger.info(
            "Claim decision reason created in repository",
            extra=build_log_extra(
                event="claim_repository_decision_reason_create_completed",
                claim_decision_id=claim_decision_id,
                reason_code=reason_code,
            ),
        )
        return reason

    # --- UpdateClaimStatusPort ---

    def update_claim_status(
        self,
        claim_id: int,
        status: ClaimStatus,
    ) -> None:
        claim = self.session.get(Claim, claim_id)
        claim.status_id = status
        self.session.add(claim)
        self.session.flush()
        logger.info(
            "Claim status updated in repository",
            extra=build_log_extra(
                event="claim_repository_status_update_completed",
                claim_id=claim_id,
                status=status,
            ),
        )

    def save_uploaded_claim_evidence(
        self,
        claim_evidence: DomainClaimEvidence,
    ) -> uuid.UUID:
        claim_evidence_model = ClaimEvidenceModel(
            sds_file_name=claim_evidence.sds_file_name,
            file_name=claim_evidence.file_name,
        )
        self.session.add(claim_evidence_model)
        self.session.flush()
        claim_evidence_id = claim_evidence_model.claim_evidence_id
        self.session.commit()
        logger.info(
            "Claim evidence persisted",
            extra=build_log_extra(
                event="claim_repository_evidence_create_completed",
                claim_evidence_id=str(claim_evidence_id),
            ),
        )
        return claim_evidence_id

    def get_claim_evidence_by_id(
        self,
        claim_evidence_id: uuid.UUID,
    ) -> DomainClaimEvidence | None:
        claim_evidence_model = self.session.get(ClaimEvidenceModel, claim_evidence_id)
        if claim_evidence_model is None:
            return None
        return DomainClaimEvidence(
            sds_file_name=claim_evidence_model.sds_file_name,
            file_name=claim_evidence_model.file_name,
        )

    def delete_claim_evidence_by_id(
        self,
        claim_evidence_id: uuid.UUID,
    ) -> bool:
        claim_evidence_model = self.session.get(ClaimEvidenceModel, claim_evidence_id)
        if claim_evidence_model is None:
            logger.info(
                "Claim evidence delete requested for missing id",
                extra=build_log_extra(
                    event="claim_repository_evidence_delete_not_found",
                    claim_evidence_id=str(claim_evidence_id),
                ),
            )
            return False
        self.session.delete(claim_evidence_model)
        self.session.flush()
        self.session.commit()
        logger.info(
            "Claim evidence deleted in repository",
            extra=build_log_extra(
                event="claim_repository_evidence_delete_completed",
                claim_evidence_id=str(claim_evidence_id),
            ),
        )
        return True
