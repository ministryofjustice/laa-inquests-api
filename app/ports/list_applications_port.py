from abc import ABC, abstractmethod

from app.models.application.index import Application


class ListApplicationsPort(ABC):
    @abstractmethod
    def list_applications(self) -> list[Application]: ...
