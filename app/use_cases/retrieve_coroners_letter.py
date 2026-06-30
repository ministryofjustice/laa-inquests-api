from sqlmodel import Session

from app.models.application.index import Application, CoronersLetterResult
from app.ports.sds_port import SdsPort
from app.use_cases.exceptions import CoronersLetterNotFoundError


class RetrieveCoronersLetterUseCase:
    def __init__(self, session: Session, sds_port: SdsPort) -> None:
        self.session = session
        self.sds_port = sds_port

    def execute(self, laa_reference: str) -> CoronersLetterResult:
        application = self.session.get(Application, int(laa_reference))
        if application is None or application.coroners_letter is None:
            raise CoronersLetterNotFoundError("Could not retrieve coroners letter")
        sds_file_name = application.coroners_letter.sds_file_name

        return CoronersLetterResult(
            file_name=application.coroners_letter.file_name,
            content=self.sds_port.retrieve_coroners_letter(sds_file_name),
        )
