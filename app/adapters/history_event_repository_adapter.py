import logging

from sqlmodel import Session, select

from app.logging_utils import build_log_extra
from app.models.history.enums import ActorType, HistoryEventReference
from app.models.history.index import HistoryEvent
from app.ports.create_history_event_port import CreateHistoryEventPort
from app.ports.get_application_history_port import GetApplicationHistoryPort

logger = logging.getLogger(__name__)


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
            laa_reference=12345,
            event_data={"related_link": "/application/12345", "context": "Optional context"}
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
        laa_reference: int,
        event_data: dict | None = None,
    ) -> HistoryEvent:
        """
        Create a new history event record.

        Args:
            event_reference: Event identifier (e.g., "EVT-BUS-APP-001")
            actor: User or system that triggered the event
            laa_reference: LAA reference number (as int)
            event_data: Optional JSON data associated with the event
                       (e.g., {"related_link": "/path", "context": "text"})

        Returns:
            The created HistoryEvent with auto-generated id and timestamp
        """
        if event_reference is None:
            raise ValueError(
                "Event reference must be provided for history event creation."
            )
        if actor is None:
            raise ValueError("Actor must be provided for history event creation.")
        if actor_type is None:
            raise ValueError("Actor type must be provided for history event creation.")
        if laa_reference is None:
            raise ValueError(
                "LAA reference must be provided for history event creation."
            )

        new_event = HistoryEvent(
            event_reference=event_reference,
            actor=actor,
            actor_type=actor_type,
            laa_reference=laa_reference,
            event_data=event_data,
        )
        self.session.add(new_event)
        self.session.flush()
        self.session.refresh(new_event)
        logger.debug(
            "History event created",
            extra=build_log_extra(
                event="history_event_created",
                laa_reference=laa_reference,
                history_event_id=new_event.id,
                event_reference=event_reference,
            ),
        )
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
