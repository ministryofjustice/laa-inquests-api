from abc import ABC, abstractmethod
from datetime import datetime

from app.models.claim.index import Claim


class ListAutoApprovedPoaClaimsPort(ABC):
    @abstractmethod
    def list_auto_approved_poa_claims(
        self, start: datetime, end: datetime
    ) -> list[Claim]:
        """List auto-approved POA claims submitted within the [start, end) window."""
        ...
