from abc import ABC, abstractmethod

from app.models.claim.index import ClaimDecision


class GetClaimDecisionPort(ABC):
    @abstractmethod
    def get_claim_decision_by_claim_id(self, claim_id: int) -> ClaimDecision | None: ...
