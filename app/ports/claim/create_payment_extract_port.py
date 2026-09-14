from abc import ABC, abstractmethod

from app.domain.payment_extract import PaymentExtractLine
from app.models.claim.index import ClaimPaymentExtract


class CreatePaymentExtractPort(ABC):
    @abstractmethod
    def create_payment_extract(
        self,
        claim_id: int,
        line: PaymentExtractLine,
    ) -> ClaimPaymentExtract: ...
