from abc import ABC, abstractmethod


class DuplicateApplicationsPort(ABC):
    @abstractmethod
    def identify_duplicates(self, application_id: int) -> list[int]: ...

    # @abstractmethod
    # def create_duplicate(self, application: Application) -> None: ...
