from __future__ import annotations

import enum
from dataclasses import dataclass, field


class ClaimRejectionReason(str, enum.Enum):
    MAX_POA_CLAIMS_EXCEEDED = "MAX_POA_CLAIMS_EXCEEDED"
    CLAIM_EXCEEDS_SUBSTANTIVE_COST_LIMIT = "CLAIM_EXCEEDS_SUBSTANTIVE_COST_LIMIT"
    APPLICATION_CLAIMS_EXCEED_COST_LIMIT = "APPLICATION_CLAIMS_EXCEED_COST_LIMIT"


@dataclass(frozen=True)
class ClaimRejection:
    reasons: list[ClaimRejectionReason] = field(default_factory=list)

    @property
    def is_rejected(self) -> bool:
        return len(self.reasons) > 0
