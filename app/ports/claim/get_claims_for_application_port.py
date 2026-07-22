from abc import ABC, abstractmethod

from app.models.claim.index import Claim


class GetClaimsForApplicationPort(ABC):
    @abstractmethod
    def get_claims_by_laa_reference(self, laa_reference: str) -> list[Claim]: ...
