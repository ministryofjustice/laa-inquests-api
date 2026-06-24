from sqlmodel import Session

from app.models.application.index import Application, CoronersLetterResult
from app.ports.sds_port import SdsPort
from app.use_cases.exceptions import InvalidCoronersLetterDocumentIdError


class RetrieveCoronersLetterUseCase:
    def __init__(self, session: Session, sds_port: SdsPort) -> None:
        self.session = session
        self.sds_port = sds_port

    def execute(self, laa_reference: str) -> CoronersLetterResult:
        application = self.session.get(Application, int(laa_reference))
        sds_id = application.coroners_letter.sds_id
        if sds_id is None or not sds_id.strip():
            raise InvalidCoronersLetterDocumentIdError(
                "Invalid coroners letter document id"
            )

        return CoronersLetterResult(
            file_name=application.coroners_letter.file_name,
            content=self.sds_port.retrieve_coroners_letter(sds_id),
        )
