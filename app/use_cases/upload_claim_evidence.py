import uuid

from app.domain.claim_evidence import ClaimEvidence
from app.ports.claim.upload_claim_evidence_port import UploadClaimEvidencePort
from app.ports.sds_port import SdsPort
from app.use_cases.exceptions import (
    ClaimEvidenceUploadError,
    ClaimEvidenceVirusDetectedError,
)


class UploadClaimEvidenceUseCase:
    def __init__(
        self,
        sds_port: SdsPort,
        upload_claim_evidence_port: UploadClaimEvidencePort,
    ) -> None:
        self.sds_port = sds_port
        self.upload_claim_evidence_port = upload_claim_evidence_port

    def execute(
        self,
        claim_evidence: bytes,
        file_name: str,
    ) -> uuid.UUID:
        try:
            is_safe = self.sds_port.virus_check_claim_evidence(
                claim_evidence, file_name
            )
        except ClaimEvidenceUploadError as e:
            raise ClaimEvidenceUploadError(
                f"{file_name} upload failed due to server error during virus check: {e!s}"
            ) from e

        if not is_safe:
            raise ClaimEvidenceVirusDetectedError(
                f"{file_name} upload failed due to identified virus"
            )

        response_body = self.sds_port.save_claim_evidence(claim_evidence, file_name)
        if response_body.status != "SUCCESS":
            raise ClaimEvidenceUploadError(
                f"Claim evidence {file_name} was not uploaded successfully"
            )

        new_claim_evidence = ClaimEvidence(
            sds_file_name=response_body.sds_file_name,
            file_name=file_name,
        )
        return self.upload_claim_evidence_port.save_uploaded_claim_evidence(
            new_claim_evidence
        )
