from abc import ABC, abstractmethod

from app.models.application.index import Application, ApplicationCreate


class CreateApplicationPort(ABC):
    @abstractmethod
    def create_application(
        self, request: ApplicationCreate, firm_code: str
    ) -> Application: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...
