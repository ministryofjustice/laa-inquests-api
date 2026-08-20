import logging
import uuid

from app.logging_utils import build_log_extra
from app.ports.claim.delete_claim_evidence_port import DeleteClaimEvidencePort
from app.ports.claim.get_claim_evidence_port import GetClaimEvidencePort
from app.ports.sds_port import SdsPort
from app.use_cases.exceptions import (
    ClaimEvidenceDeleteError,
    ClaimEvidenceNotFoundError,
)

logger = logging.getLogger(__name__)


class DeleteClaimEvidenceUseCase:
    def __init__(
        self,
        get_claim_evidence_port: GetClaimEvidencePort,
        delete_claim_evidence_port: DeleteClaimEvidencePort,
        sds_port: SdsPort,
    ) -> None:
        self.get_claim_evidence_port = get_claim_evidence_port
        self.delete_claim_evidence_port = delete_claim_evidence_port
        self.sds_port = sds_port

    def execute(self, claim_evidence_id: uuid.UUID) -> None:
        claim_evidence = self.get_claim_evidence_port.get_claim_evidence_by_id(
            claim_evidence_id
        )
        if claim_evidence is None:
            logger.warning(
                "Claim evidence delete failed",
                extra=build_log_extra(
                    event="claim_evidence_delete_failed",
                    claim_evidence_id=str(claim_evidence_id),
                ),
            )
            raise ClaimEvidenceNotFoundError("Claim evidence not found")

        try:
            self.sds_port.delete_claim_evidence(claim_evidence.sds_file_name)
            deleted = self.delete_claim_evidence_port.delete_claim_evidence_by_id(
                claim_evidence_id
            )
            if not deleted:
                logger.warning(
                    "Claim evidence delete failed",
                    extra=build_log_extra(
                        event="claim_evidence_delete_failed",
                        claim_evidence_id=str(claim_evidence_id),
                    ),
                )
                raise ClaimEvidenceNotFoundError("Claim evidence not found")
            logger.info(
                "Claim evidence deleted",
                extra=build_log_extra(
                    event="claim_evidence_delete_completed",
                    claim_evidence_id=str(claim_evidence_id),
                ),
            )
        except ClaimEvidenceNotFoundError:
            raise
        except Exception as exc:
            logger.warning(
                "Claim evidence delete failed",
                extra=build_log_extra(
                    event="claim_evidence_delete_failed",
                    claim_evidence_id=str(claim_evidence_id),
                ),
                exc_info=True,
            )
            raise ClaimEvidenceDeleteError("Failed to delete claim evidence") from exc
