import logging

from app.logging_utils import build_log_extra
from app.ports.claim.get_claim_by_id_port import GetClaimByIdPort
from app.use_cases.exceptions import ClaimNotFoundError

logger = logging.getLogger(__name__)

class RetrieveApplicationForClaimUseCase:
    def __init__(self, get_claim_by_id_port: GetClaimByIdPort) -> None:
        self.get_claim_by_id_port = get_claim_by_id_port

    def execute(self, claim_reference: str) -> str:
        claim = self.get_claim_by_id_port.get_claim_by_reference(claim_reference)
        if claim is None or claim.application is None:
            logger.warning(
                "Application lookup for claim failed",
                extra=build_log_extra(
                    event="application_for_claim_retrieval_failed",
                    claim_reference=claim_reference,
                ),
            )
            raise ClaimNotFoundError(claim_reference)
        logger.info(
            "Application retrieved for claim",
            extra=build_log_extra(
                event="application_for_claim_retrieval_succeeded",
                claim_reference=claim_reference,
            ),
        )
        return claim.application.laa_reference
