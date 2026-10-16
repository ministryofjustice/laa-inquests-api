import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app.logging_utils import build_log_extra
from app.models.audit.index import BaseAuditEvent
from app.ports.audit_port import AuditPort
from app.use_cases.exceptions import AuditError

logger = logging.getLogger(__name__)


class AuditRepositoryAdapter(AuditPort):
    """
    Adapter for creating and persisting audit events to the database.

    This adapter implements the AuditPort and provides transaction
    support via commit() and rollback() methods.

    Example usage:
        adapter = AuditRepositoryAdapter(session)
        event = adapter.audit_event(
            audit_event=ReportAudit(
                user_email_address="user@example.com",
                report_type=ReportType.CLAIMS_BACKLOG,
                parameters={"from_date": "2024-01-01", "to_date": "2024-01-31"},
            )
        )
        adapter.commit()
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def audit_event(self, audit_event: BaseAuditEvent) -> BaseAuditEvent:
        """
        Create a new audit record.

        Args:
            audit_event: The audit event to be recorded

        Returns:
            The created audit event with auto-generated id and timestamp
        """
        try:
            self.session.add(audit_event)
            self.session.flush()
            self.session.refresh(audit_event)
        except SQLAlchemyError as exc:
            raise AuditError("Failed to write audit event") from exc
        logger.info(
            "Audit event created",
            extra=build_log_extra(
                event="audit_event_created",
                audit_event_id=audit_event.id,
            ),
        )
        return audit_event

    def commit(self) -> None:
        try:
            self.session.commit()
        except SQLAlchemyError as exc:
            raise AuditError("Failed to commit audit event") from exc

    def rollback(self) -> None:
        try:
            self.session.rollback()
        except SQLAlchemyError as exc:
            raise AuditError("Failed to roll back audit event") from exc
