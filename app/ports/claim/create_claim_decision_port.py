from abc import ABC, abstractmethod

from app.models.claim.enums import ClaimDecisionStatus
from app.models.claim.index import ClaimDecision


class CreateClaimDecisionPort(ABC):
    @abstractmethod
    def create_claim_decision(
        self,
        claim_id: int,
        decision_status: ClaimDecisionStatus,
    ) -> ClaimDecision: ...
