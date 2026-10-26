import logging

from app.logging_utils import build_log_extra
from app.ports.duplicate_applications_port import DuplicateApplicationsPort

logger = logging.getLogger(__name__)


class IdentifyDuplicateApplicationsUseCase:
    def __init__(self, duplicate_applications_port: DuplicateApplicationsPort) -> None:
        self.duplicate_applications_port = duplicate_applications_port

    def execute(self) -> None:
        applications = self.duplicate_applications_port.identify_duplicates()
        logger.info(
            "Searched for duplicate applications",
            extra=build_log_extra(
                event="applications_duplicates_check_completed",
                result_count=len(applications),
            ),
        )
        return None
