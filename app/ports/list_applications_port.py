from typing import Protocol

from app.models.application.index import Application


class ListApplicationsPort(Protocol):
    def list_applications(self) -> list[Application]: ...
