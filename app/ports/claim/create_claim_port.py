import uuid
from abc import ABC, abstractmethod
from decimal import Decimal

from app.domain.claim import Claim as DomainClaim
from app.domain.constants.claims import SUBSTANTIVE_CERTIFICATE_AMOUNT
from app.models.claim.enums import InquestOutcomeCode
from app.models.claim.index import Claim


class CreateClaimPort(ABC):
    @abstractmethod
    def create_claim(
        self,
        application_id: int,
        claim: DomainClaim,
        claimant_id: str | None,
        total_funds_remaining_after_claim: Decimal = Decimal(
            SUBSTANTIVE_CERTIFICATE_AMOUNT
        ),
    ) -> Claim: ...

    @abstractmethod
    def link_evidence_to_claim(
        self,
        claim_id: int,
        evidence_ids: list[uuid.UUID],
    ) -> None: ...

    @abstractmethod
    def link_inquest_outcomes_to_claim(
        self,
        claim_id: int,
        inquest_outcomes: list[InquestOutcomeCode],
    ) -> None: ...

    @abstractmethod
    def link_cost_template_to_claim(
        self,
        claim_id: int,
        file_id: uuid.UUID,
        file_name: str,
    ) -> None: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...
