import uuid
from abc import ABC, abstractmethod


class DeleteClaimEvidencePort(ABC):
    @abstractmethod
    def delete_claim_evidence_by_id(
        self,
        claim_evidence_id: uuid.UUID,
    ) -> bool: ...
