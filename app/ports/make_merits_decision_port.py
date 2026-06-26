from typing import Protocol

from app.models.application.index import Application, ApplicationProceeding
from app.ports.application_lookup_port import ApplicationLookupPort


class MakeMeritsDecisionPort(ApplicationLookupPort, Protocol):
    def persist_merits_decision(
        self,
        application: Application,
        proceeding: ApplicationProceeding,
    ) -> None: ...
