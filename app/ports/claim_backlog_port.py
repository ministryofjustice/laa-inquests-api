from abc import ABC, abstractmethod

from app.models.claim.index import Claim


class ClaimBacklogPort(ABC):
    @abstractmethod
    def get_submitted_claims(self) -> list[Claim]: ...
