from abc import ABC, abstractmethod


class DuplicateApplicationsPort(ABC):
    @abstractmethod
    def identify_duplicates(self, application_id: int) -> list[int]: ...

    @abstractmethod
    def create_duplicate_records(
        self, application_id: int, duplicate_ids: list[int]
    ) -> None: ...

    @abstractmethod
    def get_potential_duplicates(self, application_id: int) -> list[int]: ...
