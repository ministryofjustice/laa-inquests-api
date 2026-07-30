import uuid
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
    def link_evidence_to_claim(
        self,
        claim_id: int,
        evidence_ids: list[uuid.UUID],
    ) -> None: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...
