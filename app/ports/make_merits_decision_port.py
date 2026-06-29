from abc import abstractmethod

from app.models.application.index import Application, ApplicationProceeding
from app.ports.application_lookup_port import ApplicationLookupPort


class MakeMeritsDecisionPort(ApplicationLookupPort):
    @abstractmethod
    def persist_merits_decision(
        self,
        application: Application,
        proceeding: ApplicationProceeding,
    ) -> None: ...
