from typing import Protocol

from app.models.application.index import Application, ApplicationCreate


class CreateApplicationPort(Protocol):
    def create_application(self, request: ApplicationCreate) -> Application: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
