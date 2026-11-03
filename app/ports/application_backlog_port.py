from abc import ABC, abstractmethod

from app.domain.application_backlog_report import ApplicationBacklogRecord
from app.models.application.index import Application


class ApplicationBacklogPort(ABC):
    @abstractmethod
    def get_pending_applications(self) -> list[Application]: ...

    @abstractmethod
    def get_application_backlog_records(self) -> list[ApplicationBacklogRecord]: ...
