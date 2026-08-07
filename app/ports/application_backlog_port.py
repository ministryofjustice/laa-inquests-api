from abc import ABC, abstractmethod

from app.models.application.index import Application


class ApplicationBacklogPort(ABC):
    @abstractmethod
    def get_pending_applications(self) -> list[Application]: ...
