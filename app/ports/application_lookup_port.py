from abc import ABC, abstractmethod

from app.models.application.index import Application


class ApplicationLookupPort(ABC):
    @abstractmethod
    def get_application_by_laa_reference(
        self, laa_reference: str
    ) -> Application | None: ...
