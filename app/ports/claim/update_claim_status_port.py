from abc import ABC, abstractmethod

from app.models.claim.enums import ClaimStatus


class UpdateClaimStatusPort(ABC):
    @abstractmethod
    def update_claim_status(
        self,
        claim_id: int,
        status: ClaimStatus,
    ) -> None: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...
