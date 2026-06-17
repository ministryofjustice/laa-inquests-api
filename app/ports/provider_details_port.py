from typing import Protocol


class ProviderDetailsPort(Protocol):
    def get_firm_name(self, firm_code: str) -> str | None: ...
