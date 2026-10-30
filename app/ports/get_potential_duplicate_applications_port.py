from abc import ABC, abstractmethod

from app.models.application.index import Application


class GetPotentialDuplicateApplicationsPort(ABC):
    @abstractmethod
    def get_potential_duplicate_application_ids(
        self, application_id: int
    ) -> list[int]: ...

    @abstractmethod
    def get_duplicate_applications_by_ids(
        self, application_ids: list[int]
    ) -> list[Application]: ...
