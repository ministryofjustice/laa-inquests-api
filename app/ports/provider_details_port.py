from abc import ABC, abstractmethod

from app.models.application.index import Address


class ProviderDetailsPort(ABC):
    @abstractmethod
    def get_firm_name(self, firm_code: str) -> str: ...

    @abstractmethod
    def get_office_address(self, office_id: str) -> Address: ...

    @abstractmethod
    def get_advocate_firms(self) -> dict[str, str]: ...
