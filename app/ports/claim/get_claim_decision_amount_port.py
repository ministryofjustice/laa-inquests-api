from abc import ABC, abstractmethod

from app.models.claim.index import ClaimDecisionAmount


class GetClaimDecisionAmountPort(ABC):
    @abstractmethod
    def get_claim_decision_amount_by_decision_id(
        self, claim_decision_id: int
    ) -> ClaimDecisionAmount | None: ...
