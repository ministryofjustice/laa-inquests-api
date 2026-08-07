from abc import ABC, abstractmethod

from app.models.history.enums import ActorType, EventReference
from app.models.history.index import HistoryEvent


class CreateHistoryEventPort(ABC):
    @abstractmethod
    def create_history_event(
        self,
        event_reference: EventReference,
        actor: str,
        actor_type: ActorType,
        event_description: str,
        laa_reference: str,
        event_data: str | None = None,
    ) -> HistoryEvent: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...
