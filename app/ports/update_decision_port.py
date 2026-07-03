from abc import abstractmethod

from app.models.application.index import ApplicationProceeding
from app.ports.application_lookup_port import ApplicationLookupPort


class ApplicationDecisionPort(ApplicationLookupPort):
    @abstractmethod
    def update_decision(
        self,
        proceeding: ApplicationProceeding,
    ) -> None: ...
