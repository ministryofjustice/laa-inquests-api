from abc import ABC, abstractmethod

from app.models.application.index import Application


class DuplicateApplicationsPort(ABC):
    @abstractmethod
    def identify_duplicates(self, application_id: int) -> list[Application]: ...

    # @abstractmethod
    # def create_duplicate(self, application: Application) -> None: ...
