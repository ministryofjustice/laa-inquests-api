from dataclasses import dataclass


@dataclass(frozen=True)
class ClaimEvidence:
    sds_file_name: str
    file_name: str
