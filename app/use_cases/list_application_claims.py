from app.models.claim.enums import ClaimStatus
from app.models.claim.index import Claim
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.claim.get_claims_for_application_port import (
    GetClaimsForApplicationPort,
)
from app.use_cases.exceptions import ApplicationNotFoundError


class ListApplicationClaimsUseCase:
    def __init__(
        self,
        get_claims_for_application_port: GetClaimsForApplicationPort,
        application_lookup_port: ApplicationLookupPort,
    ) -> None:
        self.get_claims_for_application_port = get_claims_for_application_port
        self.application_lookup_port = application_lookup_port

    def execute(self, laa_reference: str, assessed: bool) -> list[Claim]:
        application = self.application_lookup_port.get_application_by_laa_reference(
            laa_reference
        )
        if application is None:
            raise ApplicationNotFoundError(laa_reference)

        claims = self.get_claims_for_application_port.get_claims_by_laa_reference(
            laa_reference
        )
        if assessed:
            return [c for c in claims if c.status_id != ClaimStatus.SUBMITTED]
        return [c for c in claims if c.status_id == ClaimStatus.SUBMITTED]
