from sqlmodel import Session, select

from app.models.history.enums import ActorType, HistoryEventReference
from app.models.history.index import HistoryEvent
from app.ports.create_history_event_port import CreateHistoryEventPort
from app.ports.get_application_history_port import GetApplicationHistoryPort


class HistoryEventRepositoryAdapter(CreateHistoryEventPort, GetApplicationHistoryPort):
    """
    Adapter for creating and persisting history events to the database.

    This adapter implements the CreateHistoryEventPort and provides transaction
    support via commit() and rollback() methods.

    Example usage:
        adapter = HistoryEventRepositoryAdapter(session)
        event = adapter.create_history_event(
            event_reference=HistoryEventReference.APPLICATION_SUBMITTED,
            actor="user@example.com",
            actor_type=ActorType.PROVIDER,
            event_description="Application created",
            laa_reference=12345,
            event_data="Optional context",
            related_link="/application/12345"
        )
        adapter.commit()
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_history_event(
        self,
        event_reference: HistoryEventReference,
        actor: str,
        actor_type: ActorType,
        event_description: str,
        laa_reference: int,
        event_data: str | None = None,
        related_link: str | None = None,
    ) -> HistoryEvent:
        """
        Create a new history event record.

        Args:
            event_reference: Event identifier (e.g., "EVT-BUS-APP-001")
            actor: User or system that triggered the event
            event_description: Human-readable description of the event
            laa_reference: LAA reference number (as int)
            event_data: Optional plain text data associated with the event
            related_link: Optional URL or reference related to the event

        Returns:
            The created HistoryEvent with auto-generated id and timestamp
        """
        new_event = HistoryEvent(
            event_reference=event_reference,
            actor=actor,
            actor_type=actor_type,
            event_description=event_description,
            laa_reference=laa_reference,
            event_data=event_data,
            related_link=related_link,
        )
        self.session.add(new_event)
        self.session.flush()
        self.session.refresh(new_event)
        return new_event

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def get_application_history(self, laa_reference: int) -> list[HistoryEvent]:
        """
        Retrieve the history events of an application.

        Args:
            laa_reference: The LAA reference of the application

        Returns:
            List of history events for the application
        """
        return self.session.exec(
            select(HistoryEvent)
            .where(HistoryEvent.laa_reference == laa_reference)
            .order_by(HistoryEvent.timestamp.desc())
        ).all()
