from app.models.application.index import Application
from app.ports.list_applications_port import ListApplicationsPort


class ListApplicationsUseCase:
    def __init__(self, list_applications_port: ListApplicationsPort) -> None:
        self.list_applications_port = list_applications_port

    def execute(self) -> list[Application]:
        return self.list_applications_port.list_applications()
