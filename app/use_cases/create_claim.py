from dataclasses import dataclass
from decimal import Decimal

from app.domain.claim import Claim as DomainClaim
from app.domain.claim_error import ClaimValidationError
from app.models.claim.enums import ClaimType, POAType
from app.models.claim.index import Claim
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.create_claim_port import CreateClaimPort
from app.use_cases.exceptions import InvalidClaimError


@dataclass(frozen=True)
class CreateClaimCommand:
    laa_reference: str
    claim_type: ClaimType
    poa_type: POAType | None
    net: Decimal | None
    gross: Decimal | None
    vat_zero_total: Decimal | None
    claimant_id: str | None


class CreateClaimUseCase:
    def __init__(
        self,
        create_claim_port: CreateClaimPort,
        application_lookup_port: ApplicationLookupPort,
    ) -> None:
        self.create_claim_port = create_claim_port
        self.application_lookup_port = application_lookup_port

    def execute(self, command: CreateClaimCommand) -> Claim:
        try:
            validated_claim = DomainClaim(
                claim_type=command.claim_type,
                poa_type=command.poa_type,
                net=command.net,
                gross=command.gross,
                vat_zero_total=command.vat_zero_total,
            )
            validated_claim.validate_total_claim_cost()
        except ClaimValidationError as e:
            raise InvalidClaimError(code=e.code, message=e.message) from e

        claim = self.create_claim_port.create_claim(
            laa_reference=command.laa_reference,
            claim=validated_claim,
            claimant_id=command.claimant_id,
        )
        self.create_claim_port.commit()

        application = self.application_lookup_port.get_application_by_laa_reference(
            command.laa_reference
        )
        if application is not None:
            validated_claim.should_auto_reject_for_limit(application)

        return claim
