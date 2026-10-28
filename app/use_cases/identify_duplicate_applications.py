import logging

from app.logging_utils import build_log_extra
from app.ports.duplicate_applications_port import DuplicateApplicationsPort

logger = logging.getLogger(__name__)


class IdentifyDuplicateApplicationsUseCase:
    def __init__(self, duplicate_applications_port: DuplicateApplicationsPort) -> None:
        self.duplicate_applications_port = duplicate_applications_port

    def execute(self, application_id: int) -> None:
        duplicate_application_ids = (
            self.duplicate_applications_port.identify_duplicates(application_id)
        )
        logger.info(
            "Searched for duplicate applications",
            extra=build_log_extra(
                event="applications_duplicates_check_completed",
                result_count=len(duplicate_application_ids),
            ),
        )

        if not duplicate_application_ids:
            return

        self.duplicate_applications_port.create_duplicate_records(
            application_id, duplicate_application_ids
        )
        logger.info(
            "Created duplicate application records",
            extra=build_log_extra(
                event="applications_duplicate_records_created",
                result_count=len(duplicate_application_ids),
            ),
        )
