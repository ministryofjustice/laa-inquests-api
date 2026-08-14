import logging
import uuid

from app.logging_utils import build_log_extra
from app.models.claim.index import ClaimEvidenceResult
from app.ports.claim.get_claim_evidence_port import GetClaimEvidencePort
from app.ports.sds_port import SdsPort
from app.use_cases.exceptions import (
    ClaimEvidenceNotFoundError,
    ClaimEvidenceRetrievalError,
)

logger = logging.getLogger(__name__)


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
            logger.warning(
                "Claim evidence retrieval failed",
                extra=build_log_extra(
                    event="claim_evidence_retrieval_failed",
                    claim_evidence_id=str(claim_evidence_id),
                ),
            )
            raise ClaimEvidenceNotFoundError("Could not retrieve claim evidence")

        try:
            content = self.sds_port.retrieve_claim_evidence(
                claim_evidence.sds_file_name
            )
        except Exception as exception:
            logger.warning(
                "Claim evidence retrieval failed",
                extra=build_log_extra(
                    event="claim_evidence_retrieval_failed",
                    claim_evidence_id=str(claim_evidence_id),
                ),
                exc_info=True,
            )
            raise ClaimEvidenceRetrievalError(
                "Failed to retrieve claim evidence"
            ) from exception

        result = ClaimEvidenceResult(
            file_name=claim_evidence.file_name,
            content=content,
        )
        logger.info(
            "Claim evidence retrieved",
            extra=build_log_extra(
                event="claim_evidence_retrieval_completed",
                claim_evidence_id=str(claim_evidence_id),
                # COPILOT TODO: We shouldn't log the file name here or anywhere else
                file_name=claim_evidence.file_name,
            ),
        )
        return result
