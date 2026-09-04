from abc import ABC, abstractmethod

from app.models.claim.index import Claim


class GetClaimsForApplicationPort(ABC):
    @abstractmethod
    def get_claims_by_application_id(self, application_id: int) -> list[Claim]: ...
