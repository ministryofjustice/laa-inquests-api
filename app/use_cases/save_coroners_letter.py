from app.models.application.index import CoronersLetterResponse
from app.ports.sds_port import SdsPort
from app.use_cases.exceptions import CoronersLetterSaveError
from sqlmodel import Session
from app.models.application.index import CoronersLetter


class SaveCoronersLetterUseCase:
    def __init__(self, sds_port: SdsPort, session: Session) -> None:
        self.sds_port = sds_port
        self.session = session

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
        if response_body.status == "SUCCESS":
            new_coroners_letter = CoronersLetter(
                sds_file_name=response_body.sds_file_name,
                file_name=file_name,
            )
            self.session.add(new_coroners_letter)
            self.session.flush()
            coroners_letter_id = new_coroners_letter.coroners_letter_id
            self.session.commit()

            return CoronersLetterResponse(coroners_letter_id=coroners_letter_id)
        else:
            raise CoronersLetterSaveError(
                f"Coroners letter {file_name} was not uploaded successfully"
            )
