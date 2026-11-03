from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ApplicationBacklogRecord:
    laa_reference: str
    merits_decision: str
    created_at: datetime
    firm_code: str
    office_id: str
    proceeding_description: str | None
    matter_type: str | None
    potential_duplicate_applications: list[str]
