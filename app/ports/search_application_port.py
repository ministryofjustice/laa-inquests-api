from abc import ABC, abstractmethod

from app.models.application.index import Application


class SearchApplicationPort(ABC):
    @abstractmethod
    def search_applications(
        self, laa_reference: str, firm_code: str
    ) -> list[Application]: ...
