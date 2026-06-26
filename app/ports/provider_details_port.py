from abc import ABC, abstractmethod


class ProviderDetailsPort(ABC):
    @abstractmethod
    def get_firm_name(self, firm_code: str) -> str | None: ...
