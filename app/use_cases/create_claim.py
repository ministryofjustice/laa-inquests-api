from app.domain.claim_cost import ClaimCost
from app.domain.claim_error import ClaimValidationError
from app.models.claim.index import Claim, ClaimCreate
from app.ports.create_claim_port import CreateClaimPort
from app.use_cases.exceptions import InvalidClaimError


class CreateClaimUseCase:
    def __init__(self, create_claim_port: CreateClaimPort) -> None:
        self.create_claim_port = create_claim_port

    def execute(self, laa_reference: str, request: ClaimCreate) -> Claim:
        try:
            ClaimCost(
                poa_type=request.poa_type_id,
                net=request.total_profit_cost_net,
                gross=request.total_profit_cost_gross,
                vat_zero_total=request.total_profit_cost_vat_zero,
            )
        except ClaimValidationError as e:
            raise InvalidClaimError(code=e.code, message=e.message) from e

        claim = self.create_claim_port.create_claim(laa_reference, request)
        self.create_claim_port.commit()
        return claim
