from sqlmodel import Session, select

from app.domain.claim import Claim as DomainClaim
from app.models.claim.enums import ClaimDecisionStatus, ClaimStatus, ReasonCode
from app.models.claim.index import Claim, ClaimDecision, DecisionReason
from app.ports.claim.create_claim_decision_port import CreateClaimDecisionPort
from app.ports.claim.create_claim_port import CreateClaimPort
from app.ports.claim.create_decision_reason_port import CreateDecisionReasonPort
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
