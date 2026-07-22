from abc import ABC, abstractmethod

from app.models.claim.enums import ClaimStatus


class UpdateClaimDecisionStatusPort(ABC):
    @abstractmethod
    def update_claim_decision_status(
        self,
        claim_id: int,
        status: ClaimStatus,
    ) -> None: ...
