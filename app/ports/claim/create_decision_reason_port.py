from abc import ABC, abstractmethod

from app.models.claim.index import DecisionReason


class CreateDecisionReasonPort(ABC):
    @abstractmethod
    def create_decision_reason(
        self,
        claim_decision_id: int,
        reason_code: str,
        justification: str | None = None,
    ) -> DecisionReason: ...
