import uuid

from sqlmodel import Session, select

from app.domain.claim import Claim as DomainClaim
from app.domain.claim_evidence import ClaimEvidence as DomainClaimEvidence
from app.models.claim.enums import ClaimDecisionStatus, ClaimStatus, ReasonCode
from app.models.claim.index import (
    Claim,
    ClaimDecision,
    ClaimEvidence as ClaimEvidenceModel,
    DecisionReason,
)
from app.ports.claim.upload_claim_evidence_port import UploadClaimEvidencePort
from app.ports.claim.create_claim_decision_port import CreateClaimDecisionPort
from app.ports.claim.create_claim_port import CreateClaimPort
from app.ports.claim.create_decision_reason_port import CreateDecisionReasonPort
from app.ports.claim.get_claim_evidence_port import GetClaimEvidencePort
from app.ports.claim.get_claims_for_application_port import GetClaimsForApplicationPort
from app.ports.claim.update_claim_status_port import (
    UpdateClaimStatusPort,
)


class ClaimRepositoryAdapter(
    CreateClaimPort,
    GetClaimsForApplicationPort,
    CreateClaimDecisionPort,
    CreateDecisionReasonPort,
    UpdateClaimStatusPort,
    UploadClaimEvidencePort,
    GetClaimEvidencePort,
):
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_claim(
        self,
        laa_reference: str,
        claim: DomainClaim,
        claimant_id: str | None,
    ) -> Claim:
        new_claim = Claim(
            laa_reference=int(laa_reference),
            claim_type_id=claim.claim_type,
            total_profit_cost_net=claim.net,
            total_profit_cost_gross=claim.gross,
            total_profit_cost_vat_zero=claim.vat_zero_total,
            poa_type_id=claim.poa_type,
            claimant_id=claimant_id,
        )
        self.session.add(new_claim)
        self.session.flush()
        self.session.refresh(new_claim)
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

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def get_claims_by_laa_reference(self, laa_reference: str) -> list[Claim]:
        statement = select(Claim).where(Claim.laa_reference == int(laa_reference))
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
