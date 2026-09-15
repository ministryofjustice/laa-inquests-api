from abc import ABC, abstractmethod

from app.models.claim.index import ClaimPaymentExtract


class GetClaimPaymentExtractsPort(ABC):
    @abstractmethod
    def get_payment_extracts_for_claim(
        self, claim_id: int
    ) -> list[ClaimPaymentExtract]: ...
