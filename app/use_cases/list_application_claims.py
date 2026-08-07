from app.models.claim.enums import ClaimStatus
from app.models.claim.index import Claim
from app.ports.claim.get_claims_for_application_port import (
    GetClaimsForApplicationPort,
)


class ListApplicationClaimsUseCase:
    def __init__(
        self, get_claims_for_application_port: GetClaimsForApplicationPort
    ) -> None:
        self.get_claims_for_application_port = get_claims_for_application_port

    def execute(self, laa_reference: str, assessed: bool) -> list[Claim]:
        claims = self.get_claims_for_application_port.get_claims_by_laa_reference(
            laa_reference
        )
        if assessed:
            return [c for c in claims if c.status_id != ClaimStatus.SUBMITTED]
        return [c for c in claims if c.status_id == ClaimStatus.SUBMITTED]
