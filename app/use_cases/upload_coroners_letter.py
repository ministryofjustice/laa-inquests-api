import logging
import uuid

from app.domain.coroners_letter import CoronersLetter
from app.logging_utils import build_log_extra
from app.ports.sds_port import SdsPort
from app.ports.upload_coroners_letter_port import UploadCoronersLetterPort
from app.use_cases.exceptions import (
    CoronersLetterUploadError,
    CoronersLetterVirusCheckError,
    CoronersLetterVirusDetectedError,
)

logger = logging.getLogger(__name__)


class UploadCoronersLetterUseCase:
    def __init__(
        self,
        sds_port: SdsPort,
        upload_coroners_letter_port: UploadCoronersLetterPort,
    ) -> None:
        self.sds_port = sds_port
        self.upload_coroners_letter_port = upload_coroners_letter_port

    def execute(
        # Don't pass in the request object
        self,
        coroners_letter: bytes,
        file_name: str,
    ) -> uuid.UUID:
        try:
            is_safe = self.sds_port.virus_check_coroners_letter(
                coroners_letter, file_name
            )
        except CoronersLetterUploadError as e:
            logger.warning(
                "Coroners letter upload failed during virus check",
                extra=build_log_extra(
                    event="coroners_letter_upload_failed",
                    file_name=file_name,
                ),
                exc_info=True,
            )
            raise CoronersLetterVirusCheckError(
                f"{file_name} upload failed due to server error during virus check: {e!s}"
            ) from e

        if not is_safe:
            logger.warning(
                "Coroners letter upload failed due to virus",
                extra=build_log_extra(
                    event="coroners_letter_upload_failed",
                    file_name=file_name,
                ),
            )
            raise CoronersLetterVirusDetectedError(
                f"{file_name} upload failed due to identified virus"
            )

        response_body = self.sds_port.save_coroners_letter(
            coroners_letter,
            file_name,
        )

        if response_body.status == "SUCCESS":
            new_coroners_letter = CoronersLetter(
                sds_file_name=response_body.sds_file_name,
                file_name=file_name,
            )
            coroners_letter_id = (
                self.upload_coroners_letter_port.save_uploaded_coroners_letter(
                    new_coroners_letter
                )
            )
            logger.info(
                "Coroners letter upload completed",
                extra=build_log_extra(
                    event="coroners_letter_upload_completed",
                    coroners_letter_id=str(coroners_letter_id),
                    file_name=file_name,
                ),
            )
            return coroners_letter_id
        else:
            logger.warning(
                "Coroners letter upload failed",
                extra=build_log_extra(
                    event="coroners_letter_upload_failed",
                    file_name=file_name,
                ),
            )
            raise CoronersLetterUploadError(
                f"Coroners letter {file_name} was not uploaded successfully"
            )
