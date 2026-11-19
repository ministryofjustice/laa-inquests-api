from dataclasses import dataclass


@dataclass(frozen=True)
class ClaimEvidence:
    sds_file_name: str
    file_name: str
    office_id: str
    file_size: int | None = None
