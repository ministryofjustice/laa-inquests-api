from abc import ABC, abstractmethod

from app.models.claim.index import Claim


class GetClaimByIdPort(ABC):
    @abstractmethod
    def get_claim_by_id(self, claim_id: int) -> Claim | None: ...
