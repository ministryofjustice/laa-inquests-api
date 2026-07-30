import uuid

from app.models.claim.index import ClaimEvidenceResult
from app.ports.claim.get_claim_evidence_port import GetClaimEvidencePort
from app.ports.sds_port import SdsPort
from app.use_cases.exceptions import (
    ClaimEvidenceNotFoundError,
    ClaimEvidenceRetrievalError,
)


class RetrieveClaimEvidenceUseCase:
    def __init__(
        self,
        get_claim_evidence_port: GetClaimEvidencePort,
        sds_port: SdsPort,
    ) -> None:
        self.get_claim_evidence_port = get_claim_evidence_port
        self.sds_port = sds_port

    def execute(self, claim_evidence_id: uuid.UUID) -> ClaimEvidenceResult:
        claim_evidence = self.get_claim_evidence_port.get_claim_evidence_by_id(
            claim_evidence_id
        )
        if claim_evidence is None:
            raise ClaimEvidenceNotFoundError("Could not retrieve claim evidence")

        try:
            content = self.sds_port.retrieve_claim_evidence(
                claim_evidence.sds_file_name
            )
        except Exception as exception:
            raise ClaimEvidenceRetrievalError(
                "Failed to retrieve claim evidence"
            ) from exception

        return ClaimEvidenceResult(
            file_name=claim_evidence.file_name,
            content=content,
        )
