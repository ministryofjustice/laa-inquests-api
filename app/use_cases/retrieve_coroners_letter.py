from collections.abc import Iterator

from sqlmodel import Session

from app.models.application.index import Application
from app.ports.sds_port import SdsPort


class RetrieveCoronersLetterUseCase:
    def __init__(self, session: Session, sds_port: SdsPort) -> None:
        self.session = session
        self.sds_port = sds_port

    def execute(self, laa_reference: str) -> Iterator[bytes]:
        application = self.session.get(Application, int(laa_reference))
        return self.sds_port.retrieve_coroners_letter(
            application.coroners_letter.sds_id
        )
