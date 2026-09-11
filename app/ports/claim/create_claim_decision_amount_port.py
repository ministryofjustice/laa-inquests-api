from abc import ABC, abstractmethod
from decimal import Decimal

from app.models.claim.index import ClaimDecisionAmount


class CreateClaimDecisionAmountPort(ABC):
    @abstractmethod
    def create_claim_decision_amount(
        self,
        claim_decision_id: int,
        profit_cost_net: Decimal | None = None,
        profit_cost_gross: Decimal | None = None,
        profit_cost_vat_zero: Decimal | None = None,
        disbursement_net: Decimal | None = None,
        disbursement_gross: Decimal | None = None,
        disbursement_vat_zero: Decimal | None = None,
    ) -> ClaimDecisionAmount: ...
