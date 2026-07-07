from abc import ABC, abstractmethod

from app.models.claim.index import Claim, ClaimCreate


class CreateClaimPort(ABC):
    @abstractmethod
    def create_claim(self, laa_reference: str, request: ClaimCreate) -> Claim: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...
