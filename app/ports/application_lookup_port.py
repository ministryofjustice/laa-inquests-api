from typing import Protocol

from app.models.application.index import Application


class ApplicationLookupPort(Protocol):
    def get_application_by_laa_reference(
        self, laa_reference: str
    ) -> Application | None: ...
