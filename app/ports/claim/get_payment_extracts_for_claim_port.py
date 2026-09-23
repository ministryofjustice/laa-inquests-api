from abc import ABC, abstractmethod

from app.models.claim.index import ClaimPaymentExtract


class GetPaymentExtractsForClaimPort(ABC):
    @abstractmethod
    def get_payment_extracts_by_claim_id(
        self, claim_id: int
    ) -> list[ClaimPaymentExtract]: ...
