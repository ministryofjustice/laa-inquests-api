import uuid
from abc import ABC, abstractmethod

from app.domain.claim_evidence import ClaimEvidence


class GetClaimEvidencePort(ABC):
    @abstractmethod
    def get_claim_evidence_by_id(
        self,
        claim_evidence_id: uuid.UUID,
    ) -> ClaimEvidence | None: ...
