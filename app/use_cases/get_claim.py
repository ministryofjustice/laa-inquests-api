from app.models.claim.index import ClaimByIdResponse, ClaimDecisionResponse
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.claim.get_claim_by_id_port import GetClaimByIdPort
from app.ports.claim.get_claim_decision_port import GetClaimDecisionPort
from app.use_cases.exceptions import ApplicationNotFoundError, ClaimNotFoundError


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
            raise ApplicationNotFoundError(laa_reference)

        claim = self.get_claim_by_id_port.get_claim_by_id(claim_id)
        if claim is None or claim.laa_reference != application.laa_reference:
            raise ClaimNotFoundError(claim_id)

        response = ClaimByIdResponse.model_validate(claim)
        response.substantive_cost_limitation = (
            application.proceeding.substantive_cost_limitation
        )

        decision = self.get_claim_decision_port.get_claim_decision_by_claim_id(claim_id)
        if decision is not None:
            response.claim_decision = ClaimDecisionResponse.model_validate(decision)

        return response
