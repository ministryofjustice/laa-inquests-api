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
        print(f"Response from SDS: {response_body.status}")
        print(f"Response is string: {isinstance(response_body.status, str)}")
        if response_body.status == "201":
            print(f"Response body: {response_body}")
            response = CoronersLetterResponse.model_validate(response_body)
            print(f"Response from SDS: {response}")

            return response
        else:
            raise CoronersLetterSaveError(
                f"Coroners letter {file_name} was not uploaded successfully"
            )
