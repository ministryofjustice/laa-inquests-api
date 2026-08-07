from sqlmodel import Session

from app.models.history.enums import ActorType
from app.models.history.index import HistoryEvent
from app.ports.create_history_event_port import CreateHistoryEventPort


class HistoryEventRepositoryAdapter(CreateHistoryEventPort):
    """
    Adapter for creating and persisting history events to the database.

    This adapter implements the CreateHistoryEventPort and provides transaction
    support via commit() and rollback() methods.

    Example usage:
        adapter = HistoryEventRepositoryAdapter(session)
        event = adapter.create_history_event(
            event_reference="EVT-BUS-APP-001",
            actor="user@example.com",
            actor_type="Caseworker",
            event_description="Application created",
            laa_reference="12345",
            event_data="Optional context"
        )
        adapter.commit()

    Event reference format:
        Follow the pattern: EVT-{CATEGORY}-{ENTITY}-{NUMBER}
        Example: EVT-BUS-APP-001 (Business event, Application, sequence 001)
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_history_event(
        self,
        event_reference: str,
        actor: str,
        actor_type: ActorType,
        event_description: str,
        laa_reference: str,
        event_data: str | None = None,
    ) -> HistoryEvent:
        """
        Create a new history event record.

        Args:
            event_reference: Event identifier (e.g., "EVT-BUS-APP-001")
            actor: User or system that triggered the event
            event_description: Human-readable description of the event
            laa_reference: LAA reference number (as string, converted to int)
            event_data: Optional plain text data associated with the event

        Returns:
            The created HistoryEvent with auto-generated id and timestamp
        """
        new_event = HistoryEvent(
            event_reference=event_reference,
            actor=actor,
            actor_type=actor_type,
            event_description=event_description,
            laa_reference=int(laa_reference),
            event_data=event_data,
        )
        self.session.add(new_event)
        self.session.flush()
        self.session.refresh(new_event)
        return new_event

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
