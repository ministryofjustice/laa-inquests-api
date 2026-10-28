import logging
from datetime import datetime

from sqlmodel import Session, select

from app.contexts.user import get_entra_user_email_address, get_entra_user_object_id
from app.domain.decisions_report import (
    DECISION_EVENT_REFERENCES,
    DecisionsReportSourceRecord,
)
from app.logging_utils import build_log_extra
from app.models.application.index import Application
from app.models.claim.index import Claim
from app.models.history.enums import ActorType, HistoryEventReference
from app.models.history.index import HistoryEvent
from app.ports.create_history_event_port import CreateHistoryEventPort
from app.ports.decisions_report_port import DecisionsReportPort
from app.ports.get_application_history_port import GetApplicationHistoryPort

logger = logging.getLogger(__name__)

CLAIM_LOOKUP_BATCH_SIZE = 500


class HistoryEventRepositoryAdapter(
    CreateHistoryEventPort, GetApplicationHistoryPort, DecisionsReportPort
):
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

        actor_email_address = (
            None if actor_type == ActorType.SYSTEM else get_entra_user_email_address()
        )

        new_event = HistoryEvent(
            event_reference=event_reference,
            actor=actor,
            actor_type=actor_type,
            entra_user_object_id=entra_user_object_id,
            actor_email_address=actor_email_address,
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

    def get_decisions_report_records(
        self, decided_from: datetime, decided_before: datetime
    ) -> list[DecisionsReportSourceRecord]:
        statement = (
            select(HistoryEvent, Application.laa_reference, Application.created_at)
            .join(
                Application, HistoryEvent.application_id == Application.application_id
            )
            .where(
                HistoryEvent.event_reference.in_(DECISION_EVENT_REFERENCES),
                HistoryEvent.timestamp >= decided_from,
                HistoryEvent.timestamp < decided_before,
            )
            .order_by(HistoryEvent.timestamp, HistoryEvent.id)
        )
        rows = self.session.exec(statement).all()
        claim_submission_dates = self._get_claim_submission_dates(
            {
                claim_reference
                for event, _, _ in rows
                if (claim_reference := _claim_reference_of(event))
            }
        )

        return [
            DecisionsReportSourceRecord(
                event_reference=event.event_reference,
                decided_at=event.timestamp,
                actor=event.actor,
                actor_type=event.actor_type,
                actor_email_address=event.actor_email_address,
                event_data=event.event_data,
                laa_reference=laa_reference,
                application_submitted_at=application_created_at,
                claim_submitted_at=claim_submission_dates.get(
                    _claim_reference_of(event)
                ),
            )
            for event, laa_reference, application_created_at in rows
        ]

    def _get_claim_submission_dates(
        self, claim_references: set[str]
    ) -> dict[str, datetime]:
        references = sorted(claim_references)
        submission_dates: dict[str, datetime] = {}
        for start in range(0, len(references), CLAIM_LOOKUP_BATCH_SIZE):
            batch = references[start : start + CLAIM_LOOKUP_BATCH_SIZE]
            statement = select(Claim.claim_reference, Claim.submission_date).where(
                Claim.claim_reference.in_(batch)
            )
            submission_dates.update(self.session.exec(statement).all())
        return submission_dates


def _claim_reference_of(event: HistoryEvent) -> str | None:
    if not isinstance(event.event_data, dict):
        return None
    return event.event_data.get("claim_reference")
