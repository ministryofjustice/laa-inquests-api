from abc import ABC, abstractmethod

from app.domain.claim import Claim as DomainClaim
from app.models.claim.index import Claim


class CreateClaimPort(ABC):
    @abstractmethod
    def create_claim(
        self,
        laa_reference: str,
        claim: DomainClaim,
        claimant_id: str | None,
    ) -> Claim: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...
