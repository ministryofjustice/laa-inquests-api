from abc import ABC, abstractmethod

from app.models.history.enums import ActorType, HistoryEventReference
from app.models.history.index import HistoryEvent


class CreateHistoryEventPort(ABC):
    @abstractmethod
    def create_history_event(
        self,
        event_reference: HistoryEventReference,
        actor: str,
        actor_type: ActorType,
        application_id: int,
        event_data: dict | None = None,
    ) -> HistoryEvent: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...
