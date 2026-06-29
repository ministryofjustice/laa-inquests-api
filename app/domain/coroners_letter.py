from dataclasses import dataclass


@dataclass(frozen=True)
class CoronersLetter:
    sds_file_name: str
    file_name: str
