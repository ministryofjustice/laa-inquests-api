import uuid

from app.models.application.index import CoronersLetter
from app.ports.sds_port import SdsPort
from app.ports.upload_coroners_letter_port import UploadCoronersLetterPort
from app.use_cases.exceptions import CoronersLetterUploadError


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
        response_body = self.sds_port.save_coroners_letter(
            coroners_letter,
            file_name,
        )

        if response_body.status == "SUCCESS":
            new_coroners_letter = CoronersLetter(
                sds_file_name=response_body.sds_file_name,
                file_name=file_name,
            )
            return self.upload_coroners_letter_port.save_uploaded_coroners_letter(
                new_coroners_letter
            )
        else:
            raise CoronersLetterUploadError(
                f"Coroners letter {file_name} was not uploaded successfully"
            )
