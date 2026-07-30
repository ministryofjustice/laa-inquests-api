from abc import ABC, abstractmethod
from collections.abc import Iterator

from app.models.application.index import (
    SDSUploadClaimEvidenceResponse,
    SDSUploadCoronersLetterResponse,
)


class SdsPort(ABC):
    @abstractmethod
    def save_coroners_letter(
        self, coroners_letter: bytes, file_name: str
    ) -> SDSUploadCoronersLetterResponse: ...

    def retrieve_coroners_letter(self, file_name: str) -> Iterator[bytes]: ...

    def virus_check_coroners_letter(
        self, coroners_letter: bytes, file_name: str
    ) -> bool: ...

    def save_claim_evidence(
        self, claim_evidence: bytes, file_name: str
    ) -> SDSUploadClaimEvidenceResponse: ...

    def virus_check_claim_evidence(
        self, claim_evidence: bytes, file_name: str
    ) -> bool: ...

    def retrieve_claim_evidence(self, file_name: str) -> Iterator[bytes]: ...
