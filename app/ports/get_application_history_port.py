from abc import ABC, abstractmethod

from app.models.history.index import HistoryEvent


class GetApplicationHistoryPort(ABC):
    @abstractmethod
    def get_application_history(self, application_id: int) -> list[HistoryEvent]:
        """Retrieve the history events of an application.

        Args:
            application_id: The internal application ID

        Returns:
            List of history events for the application
        """
        ...
