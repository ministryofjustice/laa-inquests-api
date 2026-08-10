from abc import ABC, abstractmethod

from app.models.history.index import HistoryEvent


class GetApplicationHistoryPort(ABC):
    @abstractmethod
    def get_application_history(self, laa_reference: int) -> list[HistoryEvent]:
        """Retrieve the history events of an application.

        Args:
            laa_reference: The LAA reference of the application

        Returns:
            List of history events for the application
        """
        ...
