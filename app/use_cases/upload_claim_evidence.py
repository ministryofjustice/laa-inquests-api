import logging
import uuid

from app.domain.claim_evidence import ClaimEvidence
from app.logging_utils import build_log_extra
from app.ports.claim.upload_claim_evidence_port import UploadClaimEvidencePort
from app.ports.sds_port import SdsPort
from app.use_cases.exceptions import (
    ClaimEvidenceUploadError,
    ClaimEvidenceVirusCheckError,
    ClaimEvidenceVirusDetectedError,
)

logger = logging.getLogger(__name__)


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
            logger.warning(
                "Claim evidence upload failed during virus check",
                extra=build_log_extra(
                    event="claim_evidence_upload_failed",
                    file_name=file_name,
                ),
                exc_info=True,
            )
            raise ClaimEvidenceVirusCheckError(
                f"{file_name} upload failed due to server error during virus check: {e!s}"
            ) from e

        if not is_safe:
            logger.warning(
                "Claim evidence upload failed due to virus",
                extra=build_log_extra(
                    event="claim_evidence_upload_failed",
                    file_name=file_name,
                ),
            )
            raise ClaimEvidenceVirusDetectedError(
                f"{file_name} upload failed due to identified virus"
            )

        response_body = self.sds_port.save_claim_evidence(claim_evidence, file_name)
        if response_body.status != "SUCCESS":
            logger.warning(
                "Claim evidence upload failed",
                extra=build_log_extra(
                    event="claim_evidence_upload_failed",
                    file_name=file_name,
                ),
            )
            raise ClaimEvidenceUploadError(
                f"Claim evidence {file_name} was not uploaded successfully"
            )

        new_claim_evidence = ClaimEvidence(
            sds_file_name=response_body.sds_file_name,
            file_name=file_name,
        )
        claim_evidence_id = (
            self.upload_claim_evidence_port.save_uploaded_claim_evidence(
                new_claim_evidence
            )
        )
        logger.info(
            "Claim evidence upload completed",
            extra=build_log_extra(
                event="claim_evidence_upload_completed",
                claim_evidence_id=str(claim_evidence_id),
                file_name=file_name,
            ),
        )
        return claim_evidence_id
