from app.models.application.index import CoronersLetterRequest, CoronersLetterResponse
from app.ports.sds_port import SdsPort
from app.use_cases.exceptions import CoronersLetterSaveError


class SaveCoronersLetterUseCase:
    def __init__(self, sds_port: SdsPort) -> None:
        self.sds_port = sds_port

    def execute(
        self, coronersLetterRequest: CoronersLetterRequest
    ) -> CoronersLetterResponse:
        response_body = self.sds_port.save_coroners_letter(
            coronersLetterRequest.coroners_letter,
            coronersLetterRequest.file_name,
        )

        if response_body.status == 201:
            response = CoronersLetterResponse.model_validate(response_body)
            return response
        else:
            raise CoronersLetterSaveError(
                f"Coroners letter {response_body.file_name} was not uploaded successfully"
            )
