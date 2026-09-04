import logging

from sqlmodel import Session, select

from app.contexts.user import get_entra_user_object_id
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
        application_id: int,
        event_data: dict | None = None,
    ) -> HistoryEvent:
        """
        Create a new history event record.

        Args:
            event_reference: Event identifier (e.g., "EVT-BUS-APP-001")
            actor: User or system that triggered the event
            application_id: Application ID
            event_data: Optional JSON data associated with the event
                       (e.g., {"related_link": "/path", "context": "text"})

        Returns:
            The created HistoryEvent with auto-generated id and timestamp
        """
        if event_reference is None:
            raise ValueError(
                "Event reference must be provided for history event creation."
            )
        if actor is None or actor.strip() == "":
            raise ValueError("Actor must be provided for history event creation.")
        if actor_type is None:
            raise ValueError("Actor type must be provided for history event creation.")
        if application_id is None:
            raise ValueError(
                "Application ID must be provided for history event creation."
            )

        entra_user_object_id = (
            None if actor_type == ActorType.SYSTEM else get_entra_user_object_id()
        )

        new_event = HistoryEvent(
            event_reference=event_reference,
            actor=actor,
            actor_type=actor_type,
            entra_user_object_id=entra_user_object_id,
            application_id=application_id,
            event_data=event_data,
        )
        self.session.add(new_event)
        self.session.flush()
        self.session.refresh(new_event)
        logger.info(
            "History event created",
            extra=build_log_extra(
                event="history_event_created",
                history_event_id=new_event.id,
                event_reference=event_reference,
                application_id=application_id,
            ),
        )
        return new_event

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def get_application_history(self, application_id: int) -> list[HistoryEvent]:
        """
        Retrieve the history events of an application.

        Args:
            application_id: The internal application ID

        Returns:
            List of history events for the application
        """
        return self.session.exec(
            select(HistoryEvent)
            .where(HistoryEvent.application_id == application_id)
            .order_by(HistoryEvent.timestamp.desc())
        ).all()
