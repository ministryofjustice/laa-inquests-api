import logging

from app.logging_utils import build_log_extra
from app.models.claim.index import (
    ClaimByIdResponse,
    ClaimDecisionResponse,
    CostTemplateFileResponse,
)
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.claim.get_claim_by_id_port import GetClaimByIdPort
from app.ports.claim.get_claim_decision_port import GetClaimDecisionPort
from app.use_cases.exceptions import ApplicationNotFoundError, ClaimNotFoundError

logger = logging.getLogger(__name__)


class GetClaimUseCase:
    def __init__(
        self,
        get_claim_by_id_port: GetClaimByIdPort,
        get_claim_decision_port: GetClaimDecisionPort,
        application_lookup_port: ApplicationLookupPort,
    ) -> None:
        self.get_claim_by_id_port = get_claim_by_id_port
        self.get_claim_decision_port = get_claim_decision_port
        self.application_lookup_port = application_lookup_port

    def execute(self, laa_reference: str, claim_id: int) -> ClaimByIdResponse:
        application = self.application_lookup_port.get_application_by_laa_reference(
            laa_reference
        )
        if application is None:
            logger.warning(
                "Get claim failed: application not found",
                extra=build_log_extra(
                    event="claim_retrieval_failed",
                    laa_reference=laa_reference,
                    claim_id=claim_id,
                ),
            )
            raise ApplicationNotFoundError(laa_reference)

        claim = self.get_claim_by_id_port.get_claim_by_id(claim_id)
        if claim is None or claim.application_id != application.application_id:
            logger.warning(
                "Get claim failed: claim not found",
                extra=build_log_extra(
                    event="claim_retrieval_failed",
                    laa_reference=application.laa_reference,
                    claim_id=claim_id,
                ),
            )
            raise ClaimNotFoundError(claim_id)

        response = ClaimByIdResponse.model_validate(claim)
        response.substantive_cost_limitation = (
            application.proceeding.substantive_cost_limitation
        )

        decision = self.get_claim_decision_port.get_claim_decision_by_claim_id(claim_id)
        if decision is not None:
            response.claim_decision = ClaimDecisionResponse.model_validate(decision)

        if claim.claim_cost_template is not None:
            response.claim_cost_template_file = CostTemplateFileResponse.model_validate(
                claim.claim_cost_template
            )

        logger.info(
            "Claim retrieved",
            extra=build_log_extra(
                event="claim_retrieved",
                laa_reference=application.laa_reference,
                claim_id=claim.claim_id,
            ),
        )
        return response
