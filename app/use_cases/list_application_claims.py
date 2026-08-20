import logging

from app.logging_utils import build_log_extra
from app.models.claim.enums import ClaimStatus
from app.models.claim.index import ClaimSummaryResponse
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.claim.get_claim_decision_port import GetClaimDecisionPort
from app.ports.claim.get_claims_for_application_port import (
    GetClaimsForApplicationPort,
)
from app.use_cases.exceptions import ApplicationNotFoundError

logger = logging.getLogger(__name__)


class ListApplicationClaimsUseCase:
    def __init__(
        self,
        get_claims_for_application_port: GetClaimsForApplicationPort,
        get_claim_decision_port: GetClaimDecisionPort,
        application_lookup_port: ApplicationLookupPort,
    ) -> None:
        self.get_claims_for_application_port = get_claims_for_application_port
        self.get_claim_decision_port = get_claim_decision_port
        self.application_lookup_port = application_lookup_port

    def execute(self, laa_reference: str, assessed: bool) -> list[ClaimSummaryResponse]:
        application = self.application_lookup_port.get_application_by_laa_reference(
            laa_reference
        )
        if application is None:
            raise ApplicationNotFoundError(laa_reference)

        claims = self.get_claims_for_application_port.get_claims_by_laa_reference(
            laa_reference
        )
        if assessed:
            claims = [c for c in claims if c.status_id != ClaimStatus.SUBMITTED]
        else:
            claims = [c for c in claims if c.status_id == ClaimStatus.SUBMITTED]

        summaries: list[ClaimSummaryResponse] = []
        for claim in claims:
            summary = ClaimSummaryResponse.model_validate(claim)
            decision = self.get_claim_decision_port.get_claim_decision_by_claim_id(
                claim.claim_id
            )
            if decision is not None:
                summary.claim_decision_status = decision.decision
            summaries.append(summary)
        logger.info(
            "Application claims listed",
            extra=build_log_extra(
                event="application_claims_list_completed",
                laa_reference=laa_reference,
                assessed=assessed,
                result_count=len(summaries),
            ),
        )
        return summaries
