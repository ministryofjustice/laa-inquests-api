from app.models.claim.index import Claim, ClaimCreate
from app.ports.create_claim_port import CreateClaimPort


class CreateClaimUseCase:
    def __init__(self, create_claim_port: CreateClaimPort) -> None:
        self.create_claim_port = create_claim_port

    def execute(self, laa_reference: str, request: ClaimCreate) -> Claim:
        claim = self.create_claim_port.create_claim(laa_reference, request)
        self.create_claim_port.commit()
        return claim
