import logging

from app.logging_utils import build_log_extra
from app.models.application.index import CoronersLetterResult
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.sds_port import SdsPort
from app.use_cases.exceptions import (
    CoronersLetterNotFoundError,
    CoronersLetterRetrievalError,
)

logger = logging.getLogger(__name__)


class RetrieveCoronersLetterUseCase:
    def __init__(
        self, application_lookup_port: ApplicationLookupPort, sds_port: SdsPort
    ) -> None:
        self.application_lookup_port = application_lookup_port
        self.sds_port = sds_port

    def execute(self, laa_reference: str) -> CoronersLetterResult:
        application = self.application_lookup_port.get_application_by_laa_reference(
            laa_reference
        )
        if application is None or application.coroners_letter is None:
            logger.warning(
                "Coroners letter retrieval failed: letter not found",
                extra=build_log_extra(
                    event="coroners_letter_retrieval_failed",
                    laa_reference=laa_reference,
                ),
            )
            raise CoronersLetterNotFoundError("Could not retrieve coroners letter")
        sds_file_name = application.coroners_letter.sds_file_name

        try:
            content = self.sds_port.retrieve_coroners_letter(sds_file_name)
        except Exception as exception:
            logger.exception(
                "Coroners letter retrieval failed",
                extra=build_log_extra(
                    event="coroners_letter_retrieval_failed",
                    laa_reference=laa_reference,
                ),
            )
            raise CoronersLetterRetrievalError(
                "Failed to retrieve coroners letter"
            ) from exception

        logger.info(
            "Coroners letter retrieved",
            extra=build_log_extra(
                event="coroners_letter_retrieved",
                laa_reference=laa_reference,
            ),
        )
        return CoronersLetterResult(
            file_name=application.coroners_letter.file_name,
            content=content,
        )
