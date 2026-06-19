from app.models.application.index import CoronersLetterResponse
from app.ports.sds_port import SdsPort
from app.use_cases.exceptions import CoronersLetterSaveError


class SaveCoronersLetterUseCase:
    def __init__(self, sds_port: SdsPort) -> None:
        self.sds_port = sds_port

    def execute(
        # Don't pass in the request object
        self,
        coroners_letter: bytes,
        file_name: str,
    ) -> CoronersLetterResponse:
        response_body = self.sds_port.save_coroners_letter(
            coroners_letter,
            file_name,
        )

        # Port shouldn't be not return web state
        if response_body.status == 201:
            response = CoronersLetterResponse.model_validate(response_body)
            return response
        else:
            raise CoronersLetterSaveError(
                f"Coroners letter {file_name} was not uploaded successfully"
            )
