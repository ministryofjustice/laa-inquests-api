import uuid
from abc import ABC, abstractmethod

from app.domain.claim_evidence import ClaimEvidence


class UploadClaimEvidencePort(ABC):
    @abstractmethod
    def save_uploaded_claim_evidence(
        self,
        claim_evidence: ClaimEvidence,
    ) -> uuid.UUID: ...
