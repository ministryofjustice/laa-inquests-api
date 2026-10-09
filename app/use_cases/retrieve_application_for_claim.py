from app.ports.claim.get_claim_by_id_port import GetClaimByIdPort
from app.use_cases.exceptions import ClaimNotFoundError


class RetrieveApplicationForClaimUseCase:
    def __init__(self, get_claim_by_id_port: GetClaimByIdPort) -> None:
        self.get_claim_by_id_port = get_claim_by_id_port

    def execute(self, claim_reference: str) -> str:
        claim = self.get_claim_by_id_port.get_claim_by_reference(claim_reference)

        if claim is None or claim.application is None:
            raise ClaimNotFoundError(claim_reference)

        return claim.application.laa_reference
