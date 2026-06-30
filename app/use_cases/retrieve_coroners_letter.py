from sqlmodel import Session

from app.models.application.index import Application, CoronersLetterResult
from app.ports.sds_port import SdsPort
from app.use_cases.exceptions import CoronersLetterRetrievalError


class RetrieveCoronersLetterUseCase:
    def __init__(self, session: Session, sds_port: SdsPort) -> None:
        self.session = session
        self.sds_port = sds_port

    def execute(self, laa_reference: str) -> CoronersLetterResult:
        application = self.session.get(Application, int(laa_reference))
        sds_file_name = application.coroners_letter.sds_file_name
        if sds_file_name is None or not sds_file_name.strip():
            raise CoronersLetterRetrievalError("Could not retrieve coroners letter")

        return CoronersLetterResult(
            file_name=application.coroners_letter.file_name,
            content=self.sds_port.retrieve_coroners_letter(sds_file_name),
        )
