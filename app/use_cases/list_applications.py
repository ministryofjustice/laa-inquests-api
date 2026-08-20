import logging

from app.logging_utils import build_log_extra
from app.models.application.index import Application
from app.ports.list_applications_port import ListApplicationsPort

logger = logging.getLogger(__name__)


class ListApplicationsUseCase:
    def __init__(self, list_applications_port: ListApplicationsPort) -> None:
        self.list_applications_port = list_applications_port

    def execute(self) -> list[Application]:
        applications = self.list_applications_port.list_applications()
        logger.info(
            "Applications listed",
            extra=build_log_extra(
                event="applications_list_completed",
                result_count=len(applications),
            ),
        )
        return applications
