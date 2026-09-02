import logging
import uuid

from app.logging_utils import build_log_extra
from app.ports.delete_coroners_letter_port import DeleteCoronersLetterPort
from app.ports.get_coroners_letter_port import GetCoronersLetterPort
from app.ports.sds_port import SdsPort
from app.use_cases.exceptions import (
    CoronersLetterDeleteError,
    CoronersLetterNotFoundError,
)

logger = logging.getLogger(__name__)


class DeleteCoronersLetterUseCase:
    def __init__(
        self,
        get_coroners_letter_port: GetCoronersLetterPort,
        delete_coroners_letter_port: DeleteCoronersLetterPort,
        sds_port: SdsPort,
    ) -> None:
        self.get_coroners_letter_port = get_coroners_letter_port
        self.delete_coroners_letter_port = delete_coroners_letter_port
        self.sds_port = sds_port

    def execute(self, coroners_letter_id: uuid.UUID) -> None:
        coroners_letter = self.get_coroners_letter_port.get_coroners_letter_by_id(
            coroners_letter_id
        )
        if coroners_letter is None:
            logger.warning(
                "Coroners letter delete failed",
                extra=build_log_extra(
                    event="coroners_letter_delete_failed",
                    coroners_letter_id=str(coroners_letter_id),
                ),
            )
            raise CoronersLetterNotFoundError("Coroners letter not found")

        try:
            self.sds_port.delete_coroners_letter(coroners_letter.sds_file_name)
            deleted = self.delete_coroners_letter_port.delete_coroners_letter_by_id(
                coroners_letter_id
            )
            if not deleted:
                logger.warning(
                    "Coroners letter delete failed",
                    extra=build_log_extra(
                        event="coroners_letter_delete_failed",
                        coroners_letter_id=str(coroners_letter_id),
                    ),
                )
                raise CoronersLetterNotFoundError("Coroners letter not found")
            logger.info(
                "Coroners letter deleted",
                extra=build_log_extra(
                    event="coroners_letter_delete_completed",
                    coroners_letter_id=str(coroners_letter_id),
                ),
            )
        except CoronersLetterNotFoundError:
            raise
        except Exception as exc:
            logger.warning(
                "Coroners letter delete failed",
                extra=build_log_extra(
                    event="coroners_letter_delete_failed",
                    coroners_letter_id=str(coroners_letter_id),
                ),
                exc_info=True,
            )
            raise CoronersLetterDeleteError("Failed to delete coroners letter") from exc
