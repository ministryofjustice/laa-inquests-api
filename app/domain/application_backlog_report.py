from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ApplicationBacklogRecord:
    laa_reference: str
    merits_decision: str
    created_at: datetime
    firm_code: str
    proceeding_code: str
    matter_type: str | None
    potential_duplicate_applications: list[str]
