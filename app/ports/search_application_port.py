from abc import ABC, abstractmethod

from app.models.application.enums import MeritsDecision
from app.models.application.index import Application


class SearchApplicationPort(ABC):
    @abstractmethod
    def search_applications(
        self,
        laa_reference: str,
        firm_code: str,
        merits_decision: MeritsDecision | None = None,
    ) -> list[Application]: ...
