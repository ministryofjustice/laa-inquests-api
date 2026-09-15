from abc import ABC, abstractmethod

from app.models.claim.index import ClaimPaymentExtract


class ListRecoupablePoaExtractsPort(ABC):
    @abstractmethod
    def list_recoupable_poa_extracts(
        self, application_id: int
    ) -> list[ClaimPaymentExtract]:
        """List payment extract lines for PROFIT_COST, PAY_IN_FULL POA claims."""
        ...
